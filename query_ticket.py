"""Query specific ticket from database."""
import asyncio
import asyncpg

async def query_ticket():
    """Query specific ticket with customer info."""
    try:
        conn = await asyncpg.connect(
            host='localhost',
            port=5432,
            user='postgres',
            password='postgres',
            database='fte_db'
        )

        result = await conn.fetchrow('''
            SELECT t.id, conv.channel AS source_channel, t.status, t.created_at,
                   c.name, c.email
            FROM tickets t
            JOIN customers c ON t.customer_id = c.id
            JOIN conversations conv ON t.conversation_id = conv.id
            WHERE t.id = 'e950038e-0574-4b62-b26c-6b1d6955484b'
        ''')

        if result:
            print("=== Ticket Found ===\n")
            print(f"Ticket ID: {result['id']}")
            print(f"Source Channel: {result['source_channel']}")
            print(f"Status: {result['status']}")
            print(f"Created At: {result['created_at']}")
            print(f"Customer Name: {result['name']}")
            print(f"Customer Email: {result['email']}")
        else:
            print("No ticket found with that ID.")

        await conn.close()

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(query_ticket())
