import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from etl.fcc_fabric_loader import load_fabric, load_bdc


def load_from_blob(blob_name: str) -> str:
    """Download a blob to a temp file and return the temp path."""
    from azure.storage.blob import BlobServiceClient
    conn_str = os.environ["AZURE_STORAGE_CONNECTION_STRING"]
    container = os.environ.get("AZURE_STORAGE_CONTAINER", "uploads")
    client = BlobServiceClient.from_connection_string(conn_str)
    blob = client.get_container_client(container).get_blob_client(blob_name)
    tmp = tempfile.NamedTemporaryFile(suffix=".csv", delete=False)
    tmp.write(blob.download_blob().readall())
    tmp.close()
    return tmp.name


if __name__ == "__main__":
    use_blob = os.environ.get("AZURE_STORAGE_CONNECTION_STRING")

    # --- FCC Fabric ---
    fabric_local = Path("data/fabric_data.csv")
    if use_blob:
        print("Downloading fabric_data.csv from Azure Blob...")
        fabric_path = load_from_blob("fabric_data.csv")
    elif fabric_local.exists():
        fabric_path = str(fabric_local)
    else:
        print(f"ERROR: {fabric_local} not found and AZURE_STORAGE_CONNECTION_STRING not set.")
        sys.exit(1)

    print(f"Loading FCC Fabric from {fabric_path}...")
    load_fabric(fabric_path)
    print("FCC Fabric load complete.")

    # --- BDC ---
    bdc_local = Path("data/bdc_data.csv")
    if use_blob:
        print("Downloading bdc_data.csv from Azure Blob...")
        bdc_path = load_from_blob("bdc_data.csv")
    elif bdc_local.exists():
        bdc_path = str(bdc_local)
    else:
        print(f"WARNING: {bdc_local} not found, skipping BDC load.")
        bdc_path = None

    if bdc_path:
        print(f"Loading BDC from {bdc_path}...")
        load_bdc(bdc_path)
        print("BDC load complete.")
