import asyncio
from expense_agent.agent import root_agent

async def test_under_100():
    print("Testing expense under $100...")
    payload = '{"amount": 50, "submitter": "Alice", "category": "Office Supplies", "description": "Pens", "date": "2026-06-19"}'
    async for event in root_agent.run(payload):
        print("Event:", event)

async def test_over_100():
    print("\nTesting expense over $100...")
    payload = '{"amount": 150, "submitter": "Bob", "category": "Hardware", "description": "Monitor", "date": "2026-06-19"}'
    # We will get a RequestInput
    ctx = None
    async for event in root_agent.run(payload):
        print("Event:", event)
        if hasattr(event, 'interrupt_id'):
            print("Received RequestInput! Interrupt ID:", event.interrupt_id)
            print("Message:", event.message)
            ctx = event.context # context is not on RequestInput, wait
            break

async def main():
    await test_under_100()
    await test_over_100()

if __name__ == "__main__":
    asyncio.run(main())
