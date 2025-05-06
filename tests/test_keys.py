from rxdpy.keys import PrivateKey, PublicKey


def test_import_private_key_and_verify():
    priv_key_hex = "E9873D79C6D87DC0FB6A5778633389F4453213303DA61F20BD67FC233AA33262"
    
    key = PrivateKey.from_hex(priv_key_hex)

    assert key.hex() == priv_key_hex.lower()

def test_private_key_to_wif_verify():
    priv_key_hex = "0C28FCA386C7A227600B2FE50B7CAE11EC86D3BF1FBE471BE89827E19D72AA1D"
    
    key = PrivateKey.from_hex(priv_key_hex)
    
    # Test uncompressed WIF
    key.compressed = False
    wif = key.wif()
    assert wif == "5HueCGU8rMjxEXxiPuD5BDku4MkFqeZyd4dZ1jvhTVqvbTLvyTJ"
    
    # Test compressed WIF
    key.compressed = True
    wif2 = key.wif()
    assert wif2 == "KwdMAjGmerYanjeui5SHS7JkmpZvVipYvB2LJGU1ZxJwYvP98617"

def test_wif_to_private_key_uncompressed():
    wif = "5HueCGU8rMjxEXxiPuD5BDku4MkFqeZyd4dZ1jvhTVqvbTLvyTJ"
    
    key = PrivateKey(wif)
    
    private_key_hex = key.hex()
    
    assert private_key_hex == "0c28fca386c7a227600b2fe50b7cae11ec86d3bf1fbe471be89827e19d72aa1d"
    assert key.compressed is False

def test_wif_to_private_key_compressed():
    wif = "L5EZftvrYaSudiozVRzTqLcHLNDoVn7H5HSfM9BAN6tMJX8oTWz6"
    
    key = PrivateKey(wif)
    
    private_key_hex = key.hex()
    
    assert private_key_hex == "ef235aacf90d9f4aadd8c92e4b2562e1d9eb97f0df9ba3b508258739cb013db2"
    assert key.compressed is True


def test_pub_key_from_private_key():
    private_key = PrivateKey.from_hex("E9873D79C6D87DC0FB6A5778633389F4453213303DA61F20BD67FC233AA33262")
    
    pub_key = private_key.public_key()
    pub_key_hex = pub_key.hex()
    
    assert pub_key_hex == "02588d202afcc1ee4ab5254c7847ec25b9a135bbda0f2bc69ee1a714749fd77dc9"

def test_pub_key_from_hex():
    pub_key = PublicKey("02588d202afcc1ee4ab5254c7847ec25b9a135bbda0f2bc69ee1a714749fd77dc9")
    
    pub_key_hex = pub_key.hex()
    
    assert pub_key_hex == "02588d202afcc1ee4ab5254c7847ec25b9a135bbda0f2bc69ee1a714749fd77dc9"
