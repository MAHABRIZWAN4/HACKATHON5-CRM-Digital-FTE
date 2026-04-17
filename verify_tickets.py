"""Verify latest tickets in database."""
import asyncio
import asyncpg

async def verify_tickets():
    """Query latest tickets from database."""
    try:
        conn = await asyncpg.connect(
            host='localhost',
            port=5432,
            user='postgres',
            password='postgres',
            database='fte_db'
        )

        print("=== Latest 3 Tickets ===\n")

        tickets = await conn.fetch('''
            SELECT * FROM tickets ORDER BY created_at DESC LIMIT 3
        ''')

        for ticket in tickets:
            print(f"Ticket ID: {ticket['id']}")
            print(f"Title: {ticket['title']}")
            print(f"Description: {ticket['description']}")
            print(f"Status: {ticket['status']}")
            print(f"Priority: {ticket['priority']}")
            print(f"Customer ID: {ticket['customer_id']}")
            print(f"Created At: {ticket['created_at']}")
            print("-" * 60)

        await conn.close()

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(verify_tickets())
