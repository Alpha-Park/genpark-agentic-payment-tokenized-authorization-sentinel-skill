"""MCP JSON-RPC stdio server for genpark-agentic-payment-tokenized-authorization-sentinel-skill."""
import sys
import json
from client import AgenticPaymentTokenizedSentinel

sentinel = AgenticPaymentTokenizedSentinel()

def handle_call_tool(params):
    name = params.get("name")
    args = params.get("arguments", {})
    if name != "authorize_agentic_payment":
        return {"error": f"Unknown tool '{name}'"}
        
    action = args.get("action")
    if action == "create_delegation_mandate":
        return sentinel.create_delegation_mandate(
            max_spend_usd=float(args.get("max_spend_usd", 100.0)),
            allowed_merchants=args.get("allowed_merchants", ["Shopify Direct", "Instacart"]),
            duration_hours=float(args.get("duration_hours", 4.0))
        )
    elif action == "generate_ephemeral_token":
        return sentinel.generate_ephemeral_token(
            mandate_id=args.get("mandate_id", ""),
            merchant_name=args.get("merchant_name", ""),
            exact_amount_usd=float(args.get("charge_amount_usd", 0.0))
        )
    elif action == "validate_transaction_velocity":
        return sentinel.validate_transaction_velocity(
            amount_usd=float(args.get("charge_amount_usd", 0.0))
        )
    elif action == "settle_delegated_charge":
        return sentinel.settle_delegated_charge(
            payment_token=args.get("payment_token", "")
        )
    else:
        return {"error": f"Unknown action '{action}'"}

def main():
    if "--test" in sys.argv:
        print("[TEST] Running self-test for AgenticPaymentTokenizedSentinel...")
        m = sentinel.create_delegation_mandate(150.0, ["Instacart", "Walmart"])
        mid = m["mandate_id"]
        
        tok = sentinel.generate_ephemeral_token(mid, "Instacart", 45.50)
        assert "payment_token" in tok
        
        settle = sentinel.settle_delegated_charge(tok["payment_token"])
        assert settle["receipt"]["status"] == "SETTLED_COMPLETED"
        print(f"[TEST] Success! Settled Receipt: {settle['receipt']['receipt_id']}")
        return

    for line in sys.stdin:
        line = line.strip()
        if not line: continue
        try:
            try:
                req = json.loads(line)
            except json.JSONDecodeError as exc:
                print(json.dumps({"jsonrpc": "2.0", "id": None, "error": {"code": -32700, "message": str(exc)}}), flush=True)
                continue
            if not isinstance(req, dict) or req.get("jsonrpc") != "2.0" or not isinstance(req.get("method"), str):
                print(json.dumps({"jsonrpc": "2.0", "id": None, "error": {"code": -32600, "message": "Invalid Request"}}), flush=True)
                continue
            # JSON-RPC notifications never receive a response or execute request-only tools.
            if "id" not in req:
                continue
            if req["method"] == "initialize":
                print(json.dumps({"jsonrpc": "2.0", "id": req["id"], "result": {
                    "protocolVersion": "2024-11-05", "capabilities": {"tools": {}},
                    "serverInfo": {"name": 'genpark-agentic-payment-tokenized-authorization-sentinel-skill', "version": "1.0.0"}
                }}), flush=True)
                continue
            if req["method"] == "ping":
                print(json.dumps({"jsonrpc": "2.0", "id": req["id"], "result": {}}), flush=True)
                continue
            if req["method"] not in ("tools/list", "tools/call"):
                print(json.dumps({"jsonrpc": "2.0", "id": req["id"], "error": {"code": -32601, "message": "Method not found"}}), flush=True)
                continue
            if req["method"] == "tools/call":
                params = req.get("params")
                if not isinstance(params, dict) or not isinstance(params.get("arguments", {}), dict) or params.get("name") not in ('authorize_agentic_payment',):
                    print(json.dumps({"jsonrpc": "2.0", "id": req["id"], "error": {"code": -32602, "message": "Unknown tool or invalid arguments"}}), flush=True)
                    continue
            method = req.get("method")
            msg_id = req.get("id")
            
            if method == "tools/list":
                resp = {
                    "jsonrpc": "2.0",
                    "id": msg_id,
                    "result": {
                        "tools": [
                            {
                                "name": "authorize_agentic_payment",
                                "description": "Manage user-to-agent payment delegation mandates, generate ephemeral single-use cryptographic payment tokens, check velocity limits, and settle charges.",
                                "inputSchema": {
                                    "type": "object",
                                    "properties": {
                                        "action": {"type": "string", "enum": ["create_delegation_mandate", "generate_ephemeral_token", "validate_transaction_velocity", "settle_delegated_charge"]},
                                        "max_spend_usd": {"type": "number"},
                                        "allowed_merchants": {"type": "array", "items": {"type": "string"}},
                                        "mandate_id": {"type": "string"},
                                        "charge_amount_usd": {"type": "number"},
                                        "merchant_name": {"type": "string"},
                                        "payment_token": {"type": "string"}
                                    },
                                    "required": ["action"]
                                }
                            }
                        ]
                    }
                }
            elif method == "tools/call":
                res = handle_call_tool(req.get("params", {}))
                resp = {
                    "jsonrpc": "2.0",
                    "id": msg_id,
                    "result": {"content": [{"type": "text", "text": json.dumps(res, indent=2)}]}
                }
            else:
                resp = {"jsonrpc": "2.0", "id": msg_id, "result": {}}
            print(json.dumps(resp), flush=True)
        except Exception as e:
            err_resp = {"jsonrpc": "2.0", "id": req.get("id") if isinstance(req, dict) else None, "error": {"code": -32000, "message": str(e)}}
            print(json.dumps(err_resp), flush=True)

if __name__ == "__main__":
    main()
