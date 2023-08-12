from fastapi import APIRouter

router = APIRouter()


@router.get("/")
async def read_items():
    return [{"name": "Item Foo"}, {"name": "item Bar"}]


@router.get("/{item_id}")
async def read_item(item_id: int, q: str = None):
    return {"item_id": item_id, "q": q}
