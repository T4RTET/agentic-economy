import sqlite3

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from app import repositories
from app.database import get_db
from app.schemas import MarketplaceCard, MarketplaceListing, MarketplaceListingCreate, Rental, RentalCreate


router = APIRouter(prefix="/marketplace", tags=["marketplace"])


class RentalDisputeCreate(BaseModel):
    reason: str = Field(min_length=4, max_length=1000)


@router.get("/listings", response_model=list[MarketplaceCard])
def get_marketplace_listings(db: sqlite3.Connection = Depends(get_db)) -> list[MarketplaceCard]:
    return repositories.list_marketplace_cards(db)


@router.post("/agents/{agent_id}/listing", response_model=MarketplaceListing, status_code=status.HTTP_201_CREATED)
def put_agent_listing(
    agent_id: int,
    payload: MarketplaceListingCreate,
    db: sqlite3.Connection = Depends(get_db),
) -> MarketplaceListing:
    if not repositories.get_agent_or_none(db, agent_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")
    return repositories.create_or_update_listing(db, agent_id, payload)


@router.post("/listings/{listing_id}/rent", response_model=Rental, status_code=status.HTTP_201_CREATED)
def post_listing_rental(
    listing_id: int,
    payload: RentalCreate,
    db: sqlite3.Connection = Depends(get_db),
) -> Rental:
    rental = repositories.create_rental(db, listing_id, payload)
    if not rental:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Listing is not available")
    return rental


@router.get("/rentals/{rental_id}", response_model=Rental)
def get_marketplace_rental(rental_id: int, db: sqlite3.Connection = Depends(get_db)) -> Rental:
    rental = repositories.get_rental(db, rental_id)
    if not rental:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Rental not found")
    return rental


@router.get("/rentals", response_model=list[Rental])
def get_marketplace_rentals(
    renter_wallet: str | None = None,
    db: sqlite3.Connection = Depends(get_db),
) -> list[Rental]:
    return repositories.list_rentals(db, renter_wallet)


@router.post("/rentals/{rental_id}/complete", response_model=Rental)
def post_rental_complete(rental_id: int, db: sqlite3.Connection = Depends(get_db)) -> Rental:
    rental = repositories.complete_rental(db, rental_id)
    if not rental:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Active rental not found")
    return rental


@router.post("/rentals/{rental_id}/dispute", response_model=Rental)
def post_rental_dispute(
    rental_id: int,
    payload: RentalDisputeCreate,
    db: sqlite3.Connection = Depends(get_db),
) -> Rental:
    rental = repositories.dispute_rental(db, rental_id, payload.reason)
    if not rental:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Rental not found")
    return rental


@router.post("/rentals/{rental_id}/cancel", response_model=Rental)
def post_rental_cancel(rental_id: int, db: sqlite3.Connection = Depends(get_db)) -> Rental:
    rental = repositories.cancel_rental(db, rental_id)
    if not rental:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Rental cannot be cancelled")
    return rental
