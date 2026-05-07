"""Load test for Smart Investor Pro MVP.

Usage:
    python -m tests.load_test                 # default: 20 concurrent requests
    python -m tests.load_test --requests 50   # 50 concurrent requests
    python -m tests.load_test --base-url http://localhost:8000
"""
import asyncio
import httpx
import time
import sys


BASE_URL = "http://localhost:8000"
NUM_REQUESTS = 20
CONCURRENCY = 5


async def single_analysis(client: httpx.AsyncClient, token: str, i: int) -> dict:
    start = time.time()
    try:
        resp = await client.post(
            "/v1/analyze",
            json={"idea": f"Load test idea #{i} - analyze a diversified portfolio"},
            headers={"Authorization": f"Bearer {token}"}
        )
        elapsed = time.time() - start
        return {"ok": resp.status_code == 200, "status": resp.status_code, "ms": round(elapsed * 1000)}
    except Exception as e:
        return {"ok": False, "error": str(e), "ms": round((time.time() - start) * 1000)}


async def run(token: str):
    connector = httpx.AsyncHTTPTransport(limits=httpx.Limits(max_connections=CONCURRENCY))
    async with httpx.AsyncClient(base_url=BASE_URL, transport=connector, timeout=30.0) as client:
        tasks = [single_analysis(client, token, i) for i in range(NUM_REQUESTS)]
        results = await asyncio.gather(*tasks)
    return results


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Smart Investor Pro Load Test")
    parser.add_argument("--requests", type=int, default=NUM_REQUESTS, help="Number of requests")
    parser.add_argument("--concurrency", type=int, default=CONCURRENCY, help="Concurrent connections")
    parser.add_argument("--base-url", default=BASE_URL, help="API base URL")
    args = parser.parse_args()

    global BASE_URL, NUM_REQUESTS, CONCURRENCY
    BASE_URL = args.base_url
    NUM_REQUESTS = args.requests
    CONCURRENCY = args.concurrency

    start = time.time()

    async def _main():
        async with httpx.AsyncClient(base_url=BASE_URL, timeout=10.0) as client:
            r = await client.post("/auth/token")
            token = r.json()["access_token"]

        results = await run(token)
        ok = sum(1 for r in results if r["ok"])
        fail = sum(1 for r in results if not r["ok"])
        times = [r["ms"] for r in results if r["ok"]]
        avg = sum(times) / len(times) if times else 0
        p99 = sorted(times)[int(len(times) * 0.99) - 1] if len(times) >= 100 else max(times) if times else 0
        total = time.time() - start

        print(f"\n{'='*50}")
        print(f"Load Test Results")
        print(f"{'='*50}")
        print(f"  Requests:       {NUM_REQUESTS}")
        print(f"  Concurrency:    {CONCURRENCY}")
        print(f"  Duration:       {total:.2f}s")
        print(f"  Successful:     {ok}/{NUM_REQUESTS} ({ok/NUM_REQUESTS*100:.0f}%)")
        print(f"  Failed:         {fail}")
        print(f"  Avg latency:    {avg:.0f}ms")
        print(f"  P99 latency:    {p99:.0f}ms")
        print(f"  Throughput:     {NUM_REQUESTS/total:.0f} req/s")
        print(f"{'='*50}")

        if fail:
            print(f"\nFailures: {[r for r in results if not r['ok']][:3]}")
            sys.exit(1)

    asyncio.run(_main())


if __name__ == "__main__":
    main()
