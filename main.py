from fastapi import FastAPI, Form, File, UploadFile
from fastapi.responses import JSONResponse
from web3 import Web3
import hashlib, os, json, requests
from dotenv import load_dotenv
from db import create_tables, store_hashes, check_duplicate
from pydantic import BaseModel
import logging

# Logging setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# FastAPI app initialization
app = FastAPI()

# Create SQLite tables
create_tables()

# Load config from .env
RPC_URL = os.getenv("RPC_URL")
PRIVATE_KEY = os.getenv("PRIVATE_KEY")
CONTRACT_ADDRESS = Web3.to_checksum_address(os.getenv("CONTRACT_ADDRESS"))
WALLET_ADDRESS = Web3.to_checksum_address(os.getenv("WALLET_ADDRESS"))
PINATA_API_KEY = os.getenv("PINATA_API_KEY")
PINATA_API_SECRET = os.getenv("PINATA_API_SECRET")

# Connect to Ethereum node
w3 = Web3(Web3.HTTPProvider(RPC_URL))
if not w3.is_connected():
    raise Exception("Web3 connection failed")

# Load smart contract ABI
abi_path = os.path.join(os.path.dirname(__file__), "abi", "BiometricNFT.json")
with open(abi_path) as f:
    contract_abi = json.load(f)
contract = w3.eth.contract(address=CONTRACT_ADDRESS, abi=contract_abi)

# Helper: hash text (aadhaar+voter)
def sha256_hash_text(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()

# Helper: hash file content
def sha256_hash_file(file) -> str:
    content = file.read()
    file.seek(0)
    return hashlib.sha256(content).hexdigest()

# Upload file to IPFS via Pinata
def pin_file(file_obj) -> str:
    url = "https://api.pinata.cloud/pinning/pinFileToIPFS"
    headers = {
        "pinata_api_key": PINATA_API_KEY,
        "pinata_secret_api_key": PINATA_API_SECRET
    }
    files = {"file": ("file", file_obj, "application/octet-stream")}
    response = requests.post(url, files=files, headers=headers)
    response.raise_for_status()
    return response.json()["IpfsHash"]

# Upload JSON metadata to IPFS
def pin_json(payload: dict) -> str:
    url = "https://api.pinata.cloud/pinning/pinJSONToIPFS"
    headers = {
        "pinata_api_key": PINATA_API_KEY,
        "pinata_secret_api_key": PINATA_API_SECRET,
        "Content-Type": "application/json"
    }
    response = requests.post(url, data=json.dumps(payload), headers=headers)
    response.raise_for_status()
    return response.json()["IpfsHash"]

# Request model for wallet check
class WalletRequest(BaseModel):
    wallet: str

# Endpoint: Mint NFT
@app.post("/mint")
async def mint(
    aadhaar_number: str = Form(...),
    voter_number: str = Form(...),
    aadhaar_file: UploadFile = File(...),
    voter_file: UploadFile = File(...),
    photo: UploadFile = File(...),
    fingerprint: UploadFile = File(...)
):
    try:
        # Step 1: Generate hashes
        aadhaar_voter_hash = sha256_hash_text(aadhaar_number + voter_number)
        photo_hash = sha256_hash_file(photo.file)
        fingerprint_hash = sha256_hash_file(fingerprint.file)

        # Step 2: Check duplicates in DB
        if check_duplicate(aadhaar_voter_hash, photo_hash, fingerprint_hash):
            return JSONResponse(status_code=400, content={"error": "Duplicate identity exists."})

        # Step 3: Rewind files
        aadhaar_file.file.seek(0)
        voter_file.file.seek(0)
        photo.file.seek(0)
        fingerprint.file.seek(0)

        # Step 4: Upload files to IPFS
        aadhaar_ipfs = pin_file(aadhaar_file.file)
        voter_ipfs = pin_file(voter_file.file)
        photo_ipfs = pin_file(photo.file)
        fingerprint_ipfs = pin_file(fingerprint.file)

        # Step 5: Prepare metadata
        metadata = {
            "name": "Biometric Identity",
            "description": "Verified identity with biometrics",
            "image": f"ipfs://{photo_ipfs}",
            "attributes": [
                {"trait_type": "Aadhaar", "value": f"ipfs://{aadhaar_ipfs}"},
                {"trait_type": "Voter", "value": f"ipfs://{voter_ipfs}"},
                {"trait_type": "Fingerprint", "value": f"ipfs://{fingerprint_ipfs}"},
                {"trait_type": "Hash", "value": aadhaar_voter_hash[:10]}
            ]
        }

        # Step 6: Upload metadata to IPFS
        metadata_cid = pin_json(metadata)
        metadata_uri = f"ipfs://{metadata_cid}"

        # Step 7: Build and send transaction
        nonce = w3.eth.get_transaction_count(WALLET_ADDRESS)
        gas_estimate = contract.functions.mintNFT(metadata_uri).estimate_gas({
            'from': WALLET_ADDRESS,
            'nonce': nonce
        })

        txn = contract.functions.mintNFT(metadata_uri).build_transaction({
            'from': WALLET_ADDRESS,
            'nonce': nonce,
            'gas': gas_estimate + 10000,
            'gasPrice': w3.to_wei('20', 'gwei')
        })

        signed_txn = w3.eth.account.sign_transaction(txn, PRIVATE_KEY)
        tx_hash = w3.eth.send_raw_transaction(signed_txn.rawTransaction)
        receipt = w3.eth.wait_for_transaction_receipt(tx_hash)

        # Step 8: Store hashes in DB
        store_hashes(aadhaar_voter_hash, photo_hash, fingerprint_hash)

        # Done
        return {
            "tx_hash": tx_hash.hex(),
            "uri": metadata_uri,
            "status": receipt.status
        }

    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

# Endpoint: Check if wallet has already minted
@app.post("/hasMinted")
async def has_minted(request: WalletRequest):
    try:
        address = Web3.to_checksum_address(request.wallet)
        result = contract.functions.hasUserMinted(address).call()
        return {"hasMinted": result}
    except Exception as e:
        return JSONResponse(status_code=400, content={"error": str(e)})

# Optional: Health check
@app.get("/health")
async def health():
    return {
        "status": "ok",
        "web3_connected": w3.is_connected()
    }
