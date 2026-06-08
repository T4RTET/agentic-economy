import sqlite3

from fastapi import APIRouter, Depends, HTTPException, status

from app import repositories
from app.database import get_db
from app.schemas import (
    AgentTaskExecuteResponse,
    AgentTaskPlanRequest,
    AgentTaskPlanResponse,
    AutonomousTransactionRequest,
    TransactionPrepareRequest,
    TransactionRecordRequest,
)
from app.services.agent_executor import AgentExecutorError, execute_transaction_if_allowed, is_executor_enabled
from app.services.agent_intelligence import analyze_agent_passport
from app.services.agent_planner import plan_wallet_task
from app.services.transaction_service import TransactionSafetyError, prepare_transaction, record_transaction


router = APIRouter(prefix="/agents", tags=["agent tasks"])


@router.post("/{agent_id}/tasks/plan", response_model=AgentTaskPlanResponse)
def plan_agent_task(
    agent_id: int,
    payload: AgentTaskPlanRequest,
    db: sqlite3.Connection = Depends(get_db),
) -> dict:
    passport = repositories.build_passport(db, agent_id)
    if not passport:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")

    intelligence = analyze_agent_passport(passport)
    plan = plan_wallet_task(agent_id, payload.goal, passport, intelligence, payload.mode)
    plan["transaction"] = {
        "to_address": payload.to_address,
        "value_wei": payload.value_wei,
        "value_usd": payload.estimated_value_usd,
        "chain_id": payload.chain_id,
    }

    if plan["status"] != "rejected":
        try:
            prepared = prepare_transaction(
                db,
                agent_id,
                TransactionPrepareRequest(
                    to_address=payload.to_address,
                    value_wei=payload.value_wei,
                    value_usd=payload.estimated_value_usd,
                    chain_id=payload.chain_id,
                ),
                mode=payload.mode,
            )
            plan["policy"] = prepared["policy"]
            plan["transaction_request"] = prepared["transaction_request"]
        except TransactionSafetyError as exc:
            plan["status"] = "rejected"
            plan["reason"] = exc.detail

    task = repositories.create_agent_task(db, agent_id, payload.goal, plan["status"], payload.mode, plan)
    return {"task_id": task["id"], "status": task["status"], "mode": task["mode"], "plan": task["plan"], "intelligence": intelligence}


@router.post("/{agent_id}/tasks/{task_id}/execute", response_model=AgentTaskExecuteResponse)
def execute_agent_task(
    agent_id: int,
    task_id: int,
    db: sqlite3.Connection = Depends(get_db),
) -> dict:
    task = repositories.get_agent_task(db, task_id)
    if not task or task["agent_id"] != agent_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")

    passport = repositories.build_passport(db, agent_id)
    if not passport:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")
    intelligence = analyze_agent_passport(passport)
    plan = task["plan"]
    transaction = plan.get("transaction", {})

    if task["status"] == "rejected":
        return _task_response(task, intelligence, passport=passport)

    if task["mode"] == "metamask":
        try:
            prepared = prepare_transaction(
                db,
                agent_id,
                TransactionPrepareRequest(
                    to_address=transaction["to_address"],
                    value_wei=transaction["value_wei"],
                    value_usd=transaction["value_usd"],
                    chain_id=transaction["chain_id"],
                ),
                mode="metamask",
            )
        except TransactionSafetyError as exc:
            plan["status"] = "rejected"
            plan["reason"] = exc.detail
            task = repositories.update_agent_task(db, task_id, "rejected", plan)
            return _task_response(task, intelligence, passport=passport)

        plan["transaction_request"] = prepared["transaction_request"]
        task = repositories.update_agent_task(db, task_id, "requires_signature", plan)
        return _task_response(
            task,
            intelligence,
            transaction_request=prepared["transaction_request"],
            requires_user_signature=True,
            passport=passport,
        )

    if not is_executor_enabled():
        plan["status"] = "rejected"
        plan["reason"] = "Autonomous executor is disabled. Use /transactions/prepare and sign with MetaMask."
        task = repositories.update_agent_task(db, task_id, "rejected", plan)
        return _task_response(task, intelligence, passport=passport)

    try:
        request = AutonomousTransactionRequest(
            to_address=transaction["to_address"],
            value_wei=transaction["value_wei"],
            value_usd=transaction["value_usd"],
            chain_id=transaction["chain_id"],
            confirm_policy_ack=True,
        )
        result = execute_transaction_if_allowed(agent_id, request.model_dump(), passport, intelligence)
    except AgentExecutorError as exc:
        plan["status"] = "failed"
        plan["reason"] = exc.detail
        task = repositories.update_agent_task(db, task_id, "failed", plan)
        return _task_response(task, intelligence, passport=passport)

    if not result.get("executed"):
        plan["status"] = "rejected"
        plan["reason"] = result.get("reason", "Policy rejected transaction")
        task = repositories.update_agent_task(db, task_id, "rejected", plan)
        return _task_response(task, intelligence, passport=passport)

    recorded = record_transaction(
        db,
        agent_id,
        TransactionRecordRequest(
            tx_hash=result["tx_hash"],
            outcome="success",
            value_usd=transaction["value_usd"],
            metadata={"executor_address": result["executor_address"]},
        ),
        recorded_by="autonomous_executor",
    )
    plan["tx_hash"] = result["tx_hash"]
    task = repositories.update_agent_task(db, task_id, "executed", plan)
    return _task_response(
        task,
        recorded["intelligence"],
        executed=True,
        tx_hash=result["tx_hash"],
        passport=recorded["passport"],
    )


def _task_response(
    task: dict,
    intelligence: dict,
    transaction_request: dict | None = None,
    requires_user_signature: bool = False,
    executed: bool = False,
    tx_hash: str | None = None,
    passport: dict | None = None,
) -> dict:
    return {
        "task_id": task["id"],
        "status": task["status"],
        "mode": task["mode"],
        "plan": task["plan"],
        "intelligence": intelligence,
        "transaction_request": transaction_request,
        "requires_user_signature": requires_user_signature,
        "executed": executed,
        "tx_hash": tx_hash,
        "passport": passport,
    }
