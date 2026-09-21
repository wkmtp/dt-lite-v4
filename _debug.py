import asyncio
from services.adapter.bacnet import BACnetAdapter
async def main():
    from uuid import UUID
    a = BACnetAdapter(UUID('550e8400-e29b-41d4-a716-446655440000'))
    await a.connect('endpoint', 'cred', {})
    r = await a.read(['bacnet:AI:1:presentValue'])
    print('results:', len(r))
    for p in r:
        print(type(p).__name__)
    await a.disconnect()
asyncio.run(main())
