"""Quick database check script."""
import asyncio
import asyncpg

async def check_db():
    """Check database connectivity and current data."""
    try:
        conn = await asyncpg.connect(
            host='localhost',
            port=5432,
            user='postgres',
            password='postgres',
            database='fte_db'
        )

        print("[OK] Database connection successful")

        # Check tickets
        ticket_count = await conn.fetchval('SELECT COUNT(*) FROM tickets')
        print(f"[OK] Tickets in database: {ticket_count}")

        # Check customers
        customer_count = await conn.fetchval('SELECT COUNT(*) FROM customers')
        print(f"[OK] Customers in database: {customer_count}")

        # Show last 3 tickets if any
        if ticket_count > 0:
            tickets = await conn.fetch('''
                SELECT id, title, status, created_at
                FROM tickets
                ORDER BY created_at DESC
                LIMIT 3
            ''')
            print("\nLast 3 tickets:")
            for t in tickets:
                print(f"  - ID: {t['id']}, Title: {t['title']}, Status: {t['status']}")

        # Show last 3 customers if any
        if customer_count > 0:
            customers = await conn.fetch('''
                SELECT id, name, email, created_at
                FROM customers
                ORDER BY created_at DESC
                LIMIT 3
            ''')
            print("\nLast 3 customers:")
            for c in customers:
                print(f"  - ID: {c['id']}, Name: {c['name']}, Email: {c['email']}")

        await conn.close()
        return True

    except Exception as e:
        print(f"[ERROR] Database error: {e}")
        return False

if __name__ == "__main__":
    asyncio.run(check_db())
