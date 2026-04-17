"""Example usage of async database connection layer."""

import asyncio
import logging
from app.db import init_db, close_db, get_db_pool, DatabaseConfig

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)


async def main():
    """Demonstrate database connection usage."""

    # Initialize database pool
    print("Initializing database pool...")
    await init_db()

    try:
        # Get the pool instance
        db = get_db_pool()

        # Example 1: Execute a simple query
        print("\n1. Executing simple query...")
        result = await db.fetchval("SELECT COUNT(*) FROM customers")
        print(f"   Total customers: {result}")

        # Example 2: Fetch multiple rows
        print("\n2. Fetching conversations...")
        conversations = await db.fetch("""
            SELECT id, customer_id, channel, status, created_at
            FROM conversations
            ORDER BY created_at DESC
            LIMIT 5
        """)
        print(f"   Found {len(conversations)} conversations")
        for conv in conversations:
            print(f"   - {conv['id']}: {conv['channel']} ({conv['status']})")

        # Example 3: Insert data with parameters
        print("\n3. Creating test customer...")
        customer_id = await db.fetchval("""
            INSERT INTO customers (name, email, phone, company)
            VALUES ($1, $2, $3, $4)
            RETURNING id
        """, "John Doe", "john@example.com", "+1234567890", "Acme Corp")
        print(f"   Created customer: {customer_id}")

        # Example 4: Fetch single row
        print("\n4. Fetching customer details...")
        customer = await db.fetchrow("""
            SELECT id, name, email, company, created_at
            FROM customers
            WHERE id = $1
        """, customer_id)
        print(f"   Customer: {customer['name']} ({customer['email']})")

        # Example 5: Using connection context manager
        print("\n5. Using connection context manager...")
        async with db.acquire() as conn:
            # Start a transaction
            async with conn.transaction():
                # Create conversation
                conv_id = await conn.fetchval("""
                    INSERT INTO conversations (customer_id, channel, status, subject)
                    VALUES ($1, $2, $3, $4)
                    RETURNING id
                """, customer_id, "web", "active", "Test inquiry")

                # Create message
                msg_id = await conn.fetchval("""
                    INSERT INTO messages (conversation_id, sender_type, content)
                    VALUES ($1, $2, $3)
                    RETURNING id
                """, conv_id, "customer", "Hello, I need help!")

                print(f"   Created conversation: {conv_id}")
                print(f"   Created message: {msg_id}")

        # Example 6: Cleanup test data
        print("\n6. Cleaning up test data...")
        await db.execute("DELETE FROM customers WHERE id = $1", customer_id)
        print("   Test data cleaned up")

        print("\n[SUCCESS] All examples completed successfully!")

    finally:
        # Close database pool
        print("\nClosing database pool...")
        await close_db()
        print("Database pool closed")


if __name__ == "__main__":
    asyncio.run(main())
