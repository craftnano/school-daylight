"""
09_write_to_atlas.py — Push all documents to MongoDB Atlas.

PURPOSE: Drop and recreate the 'schools' collection in MongoDB Atlas,
         insert all documents from the intermediate JSON, and create indexes.
INPUTS: data/schools_pipeline.json, .env MONGO_URI
OUTPUTS: MongoDB Atlas collection "schools" in database "schooldaylight"
JOIN KEYS: None
SUPPRESSION HANDLING: None (already applied in earlier steps)
RECEIPT: phases/phase-2/receipt.md — MongoDB section
FAILURE MODES: Network timeout, auth failure, document too large
               (won't happen — max 6.4 KB per schema preflight)
"""

import os
import sys
import json

sys.path.insert(0, os.path.dirname(__file__))
from helpers import setup_logging, load_schools, FAIRHAVEN_NCESSCH

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import config


def write_to_atlas(logger):
    """Drop the schools collection, insert all documents, create indexes."""

    if not config.MONGO_URI:
        logger.error(
            "MONGO_URI is empty. Check that your .env file contains a valid "
            "MongoDB Atlas connection string. The .env file should be in the "
            "project root directory."
        )
        return False

    # Import pymongo here so the rest of the pipeline can run without it
    try:
        from pymongo import MongoClient
    except ImportError:
        logger.error(
            "pymongo is not installed. Run: pip install 'pymongo[srv]' "
            "to install it, then try again."
        )
        return False

    schools = load_schools()

    # Convert to list of documents (MongoDB wants a list for insert_many)
    documents = list(schools.values())

    # Find the largest document for logging
    largest_size = 0
    largest_id = None
    for doc in documents:
        size = len(json.dumps(doc, ensure_ascii=False).encode("utf-8"))
        if size > largest_size:
            largest_size = size
            largest_id = doc.get("_id", "unknown")

    logger.info(f"Prepared {len(documents)} documents for insertion.")
    logger.info(f"Largest document: {largest_id} ({largest_size:,} bytes).")

    # Connect to Atlas
    try:
        client = MongoClient(config.MONGO_URI, serverSelectionTimeoutMS=10000)
        # Test the connection
        client.admin.command("ping")
        logger.info("Connected to MongoDB Atlas.")
    except Exception as e:
        logger.error(
            f"Could not connect to MongoDB Atlas: {e}. "
            "This usually means: (1) your internet connection is down, "
            "(2) the connection string in .env is wrong, or "
            "(3) Atlas IP whitelist doesn't include your current IP. "
            "Check .env MONGO_URI and try again."
        )
        return False

    db = client["schooldaylight"]
    collection = db["schools"]

    # Drop existing collection — idempotent, safe to run twice
    collection.drop()
    logger.info("Dropped existing 'schools' collection.")

    # Insert all documents
    result = collection.insert_many(documents)
    logger.info(f"Inserted {len(result.inserted_ids)} documents.")

    # Create index on name field for future text search
    collection.create_index("name")
    logger.info("Created index on 'name' field.")

    # Verify count
    count = collection.count_documents({})
    logger.info(f"Verification: {count} documents in collection.")

    if count != len(documents):
        logger.error(
            f"Document count mismatch: expected {len(documents)}, got {count}. "
            "This should not happen. Check Atlas for errors."
        )
        return False

    # Fairhaven spot check
    fh_doc = collection.find_one({"_id": FAIRHAVEN_NCESSCH})
    if fh_doc:
        logger.info(
            f"Fairhaven spot check in Atlas: "
            f"name='{fh_doc.get('name')}', "
            f"enrollment={fh_doc.get('enrollment', {}).get('total')}, "
            f"join_status={fh_doc.get('metadata', {}).get('join_status')}."
        )
    else:
        logger.error(f"Fairhaven ({FAIRHAVEN_NCESSCH}) not found in Atlas after insert.")
        return False

    client.close()
    return True


def main():
    logger = setup_logging("09_write_to_atlas")
    logger.info("Step 09: Writing all documents to MongoDB Atlas.")

    success = write_to_atlas(logger)

    if success:
        logger.info("Step 09 complete.")
    else:
        logger.error("Step 09 failed. See errors above.")
        sys.exit(1)


if __name__ == "__main__":
    main()
