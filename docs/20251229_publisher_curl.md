# Seren-LLM Council Publisher Registration

Date: December 29, 2025

Use the following `curl` command to register the publisher with `x402.serendb.com`. Replace the placeholder values (`<...>`) with the actual wallet, publisher ID, and callback URL for the deployed FastAPI service before running it.

```bash
curl -X POST https://x402.serendb.com/api/publishers \
  -H "Content-Type: application/json" \
  -H "X-AGENT-WALLET: ${COUNCIL_WALLET}" \
  -H "X-Payment-Delegation: true" \
  -d '{
    "publisher_id": "<SEREN_LLM_COUNCIL_PUBLISHER_ID>",
    "name": "Seren-LLM Council",
    "description": "Multi-model AI council with 5 members plus a chairman synthesizer.",
    "callback_url": "<PUBLIC_URL>/v1/council/query",
    "pricing": {
      "currency": "USD",
      "flat_fee": "15.00"
    },
    "settlement_wallet": "<COUNCIL_WALLET>",
    "tags": ["ai", "council", "consensus"]
  }'
```

Expected success returns HTTP `201` with the new publisher record. If the request fails with `402 Payment Required`, verify the agent wallet has funds before retrying.
