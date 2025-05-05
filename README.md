# 🧠 rxdpy – Python SDK for Radiant (RXD), Glyphs

`rxdpy` is a high-performance Python library that enables seamless integration with the [Radiant Blockchain](https://radiantblockchain.org/) ecosystem, including full support for RXD transactions, Glyph-based tokens, and NFTs. Inspired by [solders](https://kevinheavey.github.io/solders/), this SDK aims to bring Radiant and Glyph capabilities to Python developers building server-side web3 applications.

---

## 🚀 Features

- 📬 **Transaction Construction & Signing**
  - Build, sign, and serialize RXD transactions
  - Lock and unlock funds for atomic swaps (coming soon)

- 🔑 **Wallet Support**
  - Key generation, address encoding/decoding
  - WIF/private key handling
  - HD wallets (BIP32/BIP39 planned)

- 🎨 **Glyph Protocol Integration**
  - Read/write Glyphs (tokens, NFTs)
  - Metadata handling
  - Mint, transfer, and inspect on-chain assets

- 📡 **Network Tools**
  - Broadcast transactions
  - UTXO queries and chain state interactions (via ElectrumX or custom RPC)

---

## 📦 Installation

Coming soon via PyPI and `maturin`:

```bash
pip install rxdpy
