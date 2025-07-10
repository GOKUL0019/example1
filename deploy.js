require("dotenv").config();
const hre = require("hardhat");

async function main() {
  const BiometricNFT = await hre.ethers.getContractFactory("BiometricNFT");
  const contract = await BiometricNFT.deploy();
  await contract.waitForDeployment();
  console.log("✅ Deployed at:", await contract.getAddress());
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});