"""
Mock Warehouse API
-------------------
Stands in for Northstar's real warehouse system, which we don't have access
to. Exposes the same shape a real inventory system would: a list of SKUs
with current stock counts. Counts drift slightly on each request so polling
actually has something new to pick up.

Run separately from the sync service:
    uvicorn warehouse_api:app --port 9000 --reload
"""

import random
from fastapi import FastAPI

app = FastAPI(title="Northstar Warehouse API (mock)")

# Seed inventory. `count` will drift over time to simulate real warehouse activity.
# SKUs are readable on purpose -- a support agent or test script shouldn't have
# to cross-reference a spreadsheet to know NS-SKILLET-10IN is a skillet.
_INVENTORY = {
    "NS-SKILLET-10IN": {"name": "Cast Iron Skillet 10in", "count": 18},
    "NS-MUG-TRAVEL": {"name": "Insulated Travel Mug", "count": 0},
    "NS-TOTE-COTTON": {"name": "Organic Cotton Tote", "count": 142},
    "NS-BOARD-BAMBOO": {"name": "Bamboo Cutting Board", "count": 6},
    "NS-POUROVER-CERAMIC": {"name": "Ceramic Pour-Over Set", "count": 27},
}


def _drift_stock():
    """Randomly nudges a couple of SKUs up or down, floor at 0."""
    for sku in random.sample(list(_INVENTORY), k=2):
        change = random.choice([-3, -1, 0, 1, 2, 5])
        _INVENTORY[sku]["count"] = max(0, _INVENTORY[sku]["count"] + change)


@app.get("/warehouse/stock")
def list_stock():
    """DEPRECATED as of Day 4 -- sync_service.py no longer calls this.
    Kept only so the Day 3 polling flow stays reproducible for the record;
    see SCOPE_DELTA.md. The live sync path is now
    simulate_warehouse_push.py -> POST /webhooks/stock-update."""
    _drift_stock()
    return [{"sku": sku, **info} for sku, info in _INVENTORY.items()]


@app.get("/warehouse/stock/{sku}")
def get_stock(sku: str):
    item = _INVENTORY.get(sku.upper())
    if not item:
        return {"sku": sku.upper(), "found": False}
    return {"sku": sku.upper(), "found": True, **item}


@app.get("/health")
def health():
    return {"status": "ok"}
