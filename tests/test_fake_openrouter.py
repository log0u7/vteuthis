import urllib.request

from tests.fake_openrouter import serve


def test_fake_serves_credits_and_completions():
    server = serve(port=0)
    port = server.server_address[1]
    import threading

    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/api/v1/credits") as r:
            assert r.status == 200
        req = urllib.request.Request(
            f"http://127.0.0.1:{port}/api/v1/chat/completions",
            data=b"{}",
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req) as r:
            assert r.status == 200
            assert b"observe" in r.read()
    finally:
        server.shutdown()
