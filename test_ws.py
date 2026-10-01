import asyncio
import websockets
import json
import requests
import time

async def test_ws():
    uri = 'ws://127.0.0.1:8000/ws'
    async with websockets.connect(uri) as ws:
        init_raw = await ws.recv()
        init_data = json.loads(init_raw)
        print('[WS TEST] Received INITIAL_STATE with', len(init_data.get('events', [])), 'events')

        t0 = time.time()
        requests.post('http://127.0.0.1:8000/api/simulate/scenario/fire')

        msg_raw = await ws.recv()
        t_delta = (time.time() - t0) * 1000
        msg_data = json.loads(msg_raw)
        msg_type = msg_data.get('type')
        cat = msg_data.get('payload', {}).get('category')
        print(f'[WS TEST] Received {msg_type} in {t_delta:.1f}ms: category={cat}')
        assert msg_type == 'INCIDENT_UPDATE'
        print('[WS TEST] WebSocket test passed successfully!')

if __name__ == '__main__':
    asyncio.run(test_ws())
