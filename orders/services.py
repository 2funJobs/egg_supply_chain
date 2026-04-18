# Blockchain operations will be managed with this file
import hashlib
import time
from .models import BlockchainTransaction

def log_to_blockchain(pallet, user, action_type, payload):
    # Yazilan bu metod ya da servis, islemi blockchaine gonderir ve donen id degerini
    # Log tablosuna kaydeder.

    # Simdilik mock bir blockchain agindan veri gelisni simule edelim. SHA-256 hash fonksiyonu
    # ile benzersiz sahte bir TxID uretilir.

    raw_data = f"{pallet.id}-{user.id}-{action_type}-{time.time()}"
    fake_tx_hash = "0x" + hashlib.sha256(raw_data.encode()).hexdigest()

    # Daha sonra bu kaydi veritabanina yazalim
    log = BlockchainTransaction.objects.create(
        pallet=pallet,
        user=user,
        action_type=action_type,
        tx_hash=fake_tx_hash,
        status="SUCCESS",
        payload=payload
    )

    return log