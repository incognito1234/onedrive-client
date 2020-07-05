import quickxorhash
import base64


def hash_of_file(file_path):
  h = quickxorhash.quickxorhash()
  BLOCK_SIZE = 1048576 * 20  # 20 MB
  with open(file_path, 'rb') as f:
    fb = f.read(BLOCK_SIZE)
    while len(fb) > 0:
      h.update(fb)
      fb = f.read(BLOCK_SIZE)
  result = base64.b64encode(h.digest()).decode()
  return result
