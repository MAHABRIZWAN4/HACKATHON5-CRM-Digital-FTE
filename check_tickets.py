import asyncio
from app.db.connection import init_db, get_db_pool, close_db

async def check():
    await init_db()
    db = get_db_pool()
    tickets = await db.fetch('''
        SELECT t.id, t.title as subject, c.channel as source_channel, t.created_at
        FROM tickets t
        JOIN conversations c ON t.conversation_id = c.id
        ORDER BY t.created_at DESC
        LIMIT 5
    ''')
    print("=== Last 5 Tickets ===")
    for t in tickets:
        print(dict(t))
    await close_db()

asyncio.run(check())
