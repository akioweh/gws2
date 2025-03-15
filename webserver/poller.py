"""
Highly experimental.
A tool to make live polls.
"""

from fastapi import APIRouter, HTTPException

router = APIRouter(
    prefix='/apps/poll'
)

running_polls = {}  # poll_id -> server location


@router.get('/create')
async def create_poll():
    pass


@router.get('/{poll_id}')
async def view_poll(poll_id: str):
    if poll_id not in running_polls:
        raise HTTPException(status_code=404, detail='Poll not found')


