from .models import BlockchainTransaction
import threading # (Opsiyonel) Blokzincir ağı bekletmesin diye basit asenkron yapı

def log_to_blockchain(pallet, user, action_type, payload):
    """
    Sistemdeki kritik işlemleri veritabanına kaydeder ve blokzincir ağına gönderir.
    """
    # 1. Güvenlik: Kullanıcının kurumunu tespit et
    organization = user.organization if user else None

    # 2. PostgreSQL'e PENDING (Bekliyor) statüsünde logu aç
    # (Eğer pallet parametresi None gelirse, null olarak kaydedilir örn: Sertifika işlemi)
    transaction_log = BlockchainTransaction.objects.create(
        pallet=pallet,
        user=user,
        organization=organization,
        action_type=action_type,
        status='PENDING',
        payload=payload
    )

    # 3. Blokzincir Ağına Gönderim (Hyperledger Fabric vs.)
    # API'nin yanıt süresini uzatmamak için bu işlemi arka planda (Thread veya Celery ile) tetikliyoruz.
    thread = threading.Thread(target=_send_to_fabric_network, args=(transaction_log.id, payload))
    thread.start()

    return transaction_log

def _send_to_fabric_network(log_id, payload):
    """
    DİKKAT: Burası Hyperledger Fabric SDK veya REST API ile konuşacak asıl kısımdır.
    Şu an için başarılı dönmüş gibi simüle ediyoruz.
    """
    try:
        # Django veritabanındaki o anki logu bul
        transaction_log = BlockchainTransaction.objects.get(id=log_id)
        
        # BURAYA HYPERLEDGER API İSTEĞİ GELECEK
        # response = requests.post("http://hyperledger-api:3000/invoke", json=payload)
        
        # Simülasyon: Hyperledger'dan başarılı bir Hash ve Block numarası döndüğünü varsayıyoruz
        mock_tx_hash = f"0xabc123fabric{transaction_log.id}hash"
        mock_block_number = 1045
        
        # İşlem başarılıysa Django'yu güncelle
        transaction_log.tx_hash = mock_tx_hash
        transaction_log.block_number = mock_block_number
        transaction_log.status = 'SUCCESS'
        transaction_log.save()
        
    except Exception as e:
        # Ağ çökerse veya hata verirse logu FAILED olarak işaretle
        transaction_log.status = 'FAILED'
        transaction_log.payload['error_detail'] = str(e)
        transaction_log.save()
# Blockchain operations will be managed with this file
# import hashlib
# import time
# from .models import BlockchainTransaction

# def log_to_blockchain(pallet, user, action_type, payload):
#     # Yazilan bu metod ya da servis, islemi blockchaine gonderir ve donen id degerini
#     # Log tablosuna kaydeder.

#     # Simdilik mock bir blockchain agindan veri gelisni simule edelim. SHA-256 hash fonksiyonu
#     # ile benzersiz sahte bir TxID uretilir.

#     raw_data = f"{pallet.id}-{user.id}-{action_type}-{time.time()}"
#     fake_tx_hash = "0x" + hashlib.sha256(raw_data.encode()).hexdigest()

#     # Daha sonra bu kaydi veritabanina yazalim
#     log = BlockchainTransaction.objects.create(
#         pallet=pallet,
#         user=user,
#         action_type=action_type,
#         tx_hash=fake_tx_hash,
#         status="SUCCESS",
#         payload=payload
#     )

#     return log