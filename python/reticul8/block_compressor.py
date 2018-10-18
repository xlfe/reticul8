import os, sys
import datetime
import zlib


class block_compressor(object):
    """
    Take a set of input bytes and using zlib compress blocks of less than or equal to block_size
    and return them as an iterator using blocks()

    Each block can be decompressed on its own (still part of the overall stream)
    """
    WBITS = 15

    #If you're tuning - tune these two params
    START_OVERSHOOT = 1.1
    OVERSHOOT_INCREASE = 0.08

    def __init__(self, in_bytes, block_size):

        def factory():
            return zlib.compressobj(zlib.Z_BEST_COMPRESSION, zlib.DEFLATED, self.WBITS)
        self.c = factory()
        self.factory = factory
        self.bs = block_size
        self.input = in_bytes.read()
        self.input_len = len(self.input)
        self.pos = 0
        self.compressed_bytes = 0

    @property
    def percent(self):
        return self.pos/self.input_len * 100

    @property
    def ratio(self):
        return self.compressed_bytes/self.pos

    @property
    def more(self):
        return self.pos != self.input_len

    def blocks(self):
        while True:
            next = self.next_block()
            if next is None:
                return
            yield next

    def check_request_size(self, size):

        if size + self.pos <= self.input_len:
            return size
        else:
            return self.input_len - self.pos

    def next_block(self):
        """
        This could probably be improved; at the moment it starts by trying to overshoot the
        desired compressed block size, then it reduces the input bytes one by one until it
        has met the required block size
        """

        assert self.pos <= self.input_len
        if self.pos == self.input_len:
            return None

        # Overshoot
        i = self.START_OVERSHOOT

        while True:
            try_size = int(self.bs * i)
            size = self.check_request_size(try_size)
            c, d = self.compress_next_chunk(size)

            if size != try_size:
                break

            if len(d) < self.bs:
                i += self.OVERSHOOT_INCREASE
            else:
                break

        # Reduce by one byte until we hit the target
        while True:

            if len(d) <= self.bs:

                self.c = c
                # self.c = self.factory()
                crc32 = zlib.crc32(self.get_input(size), 0xffffffff) & 0xffffffff
                self.pos += size
                self.compressed_bytes += len(d)
                return crc32, size, d

            size -= 1

            if size == 0:
                return None

            c, d = self.compress_next_chunk(size)


    def get_input(self, size):
        assert self.pos + size <= self.input_len
        return self.input[self.pos:self.pos + size]

    def compress_next_chunk(self, size):
        data = self.get_input(size)
        c = self.c.copy()
        # c = self.factory()
        if self.pos+size < self.input_len:
            return c, c.compress(data) + c.flush(zlib.Z_PARTIAL_FLUSH)
        else:
            return c, c.compress(data) + c.flush()






if __name__ == "__main__":

    BLOCKSIZE = 200
    filename = sys.argv[1]
    compressed_file = []

    with open(filename, 'rb') as rom:

        start = datetime.datetime.now()
        blocks = block_compressor(rom, BLOCKSIZE)
        count = 0

        for crc32, size, data in blocks.blocks():
            print ('{} {:.2f}% {} -> {}'.format(count, blocks.percent, size, len(data)))
            count += 1
            compressed_file.append(data)

        print('{}'.format(blocks.ratio))
        print('Took {} seconds to find {} chunks'.format((datetime.datetime.now() - start).total_seconds(), count))

    d = zlib.decompressobj(wbits = block_compressor.WBITS)

    decompressed = bytearray()
    for _ in compressed_file:
        decompressed += d.decompress(_)
        # decompressed += zlib.decompressobj(wbits = block_compressor.WBITS).decompress(_)

    with open(filename, 'rb') as original:
        original_data = original.read()
        assert original_data == decompressed
    print (len(original_data))




