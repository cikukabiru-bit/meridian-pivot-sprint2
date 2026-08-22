"""Northstar inventory sync service - query endpoint.

The support tool asks this service "is this in stock?" and gets an answer
from our cached copy, instantly, without touching the warehouse.
"""

from flask import Flask, jsonify, request

import stock_cache
import warehouse_poller  # ORIGINAL SPEC - removed by the Day 4 pivot

app = Flask(__name__)


@app.route("/health")
def health():
    """Is the cache populated, and how fresh is it?"""
    return jsonify(stock_cache.stats())


@app.route("/api/stock")
def stock():
    """Answer a stock question.

    Two ways to ask:
      /api/stock?q=nike                        -> search by product name
      /api/stock?product_id=P001&size=42       -> exact availability answer
    """
    query = request.args.get("q")
    product_id = request.args.get("product_id")
    size = request.args.get("size")

    if query:
        matches = stock_cache.search(query)
        return jsonify({"query": query, "count": len(matches), "matches": matches})

    if not product_id or not size:
        return (
            jsonify({"error": "provide product_id and size, or q= to search"}),
            400,
        )

    item = stock_cache.get(product_id, size)
    if item is None:
        return (
            jsonify(
                {
                    "error": "not found",
                    "product_id": product_id,
                    "size": size,
                }
            ),
            404,
        )

    return jsonify(
        {
            "product_id": item["product_id"],
            "product_name": item["product_name"],
            "size": item["size"],
            "in_stock": item["stock_quantity"] > 0,
            "stock_quantity": item["stock_quantity"],
            "restock_date": item["restock_date"],
            "as_of": stock_cache.stats()["last_updated"],
        }
    )


if __name__ == "__main__":
    warehouse_poller.start()  # ORIGINAL SPEC - removed by the Day 4 pivot
    # debug=False on purpose: Flask's auto-reloader starts the program twice,
    # which would run two pollers hitting the warehouse in parallel.
    app.run(port=5000, debug=False)
