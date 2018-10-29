import sys
import logging
import progressbar
import threading
from Queue import Queue
from web3 import Web3, IPCProvider
from logging.handlers import TimedRotatingFileHandler


class Ensread():
    def __init__(self, config):
        self.config = config
        self.start_block_no = 0
        self.exitFlag = False

        self.logger = logging.getLogger('ensread')
        root_handler = TimedRotatingFileHandler(
            filename='./ensread.log',
            when='midnight',
            backupCount=1,
            encoding=None,
            delay=False,
            utc=False)
        formatter = logging.Formatter('%(asctime)s - %(name)10s - %(levelname)5s - %(message)s')
        root_handler.setFormatter(formatter)
        root_handler.setLevel(logging.INFO)
        self.logger.setLevel(logging.INFO)
        self.logger.addHandler(root_handler)

        self.connect_to_node()
        #self.exit_if_syncing()

        self.block_q = Queue(maxsize=80)
        self.tx_threads = list()
        for i in range(self.config['no_of_threads']):
            t = ProcessENSEvent(self, i)
            t.setDaemon(True)
            t.start()
            self.tx_threads.append(t)
        self.process_blocks()

        for thread in self.tx_threads:
            thread.join()


    def connect_to_node(self):
        try:
            self.web3 = Web3(IPCProvider(self.config['ipc_file_name']))
        except Exception as e:
            self.logger.error('Could not connect to  network' + str(e))
            sys.exit(-1)

    def exit_if_syncing(self):
        sync_info = self.web3.eth.syncing
        if isinstance(sync_info, bool) == False:
            self.logger.error('Network is syncing')
            sys.exit(-1)

    def process_blocks(self):
        curr_block_number = self.web3.eth.blockNumber
        self.start_block_no = curr_block_number - (10 * int(self.config['no_of_days']))

        total = curr_block_number - self.start_block_no
        bar = progressbar.ProgressBar(maxval=total, widgets=[progressbar.Bar('=', '[', ']'), ' ', progressbar.Percentage()])
        bar.start()
        pg = 0
        for block_to_process in range(self.start_block_no, curr_block_number):
            block = self.web3.eth.getBlock(block_to_process)
            self.block_q.put(block)
            pg = pg + 1
            bar.update(pg)
        bar.finish()

        for i in range(self.config['no_of_threads']):
            self.block_q.put(None)

class ProcessENSEvent(threading.Thread):
    def __init__(self, parent, i):
        threading.Thread.__init__(self)
        self.parent = parent
        self.thread_id = i

        self.web3 = parent.web3
        self.exitFlag = parent.exitFlag
        self.logger = parent.logger

        self.logger.debug('started thread ' + str(self.thread_id))

    def run(self):
        while True:
            self.logger.debug('running thread ' + str(self.thread_id))

            block = self.parent.block_q.get()

            # kill thread signal
            if block is None:
                self.logger.debug('stopping thread ' + str(self.thread_id))
                break


            self.logger.debug('Processing block ' + str(block.number) + ' by thread ' + str(self.thread_id))

            for txHash in block.transactions:
                tx = self.web3.eth.getTransaction(txHash)
                if str(tx.to).lower() == '0x6090a6e47849629b7245dfa1ca21d94cd15878ef':

                    # Ignore receipts with status 0
                    # temp = self.web3.eth.getTransaction(txHash)
                    # if int(temp["status"]) == 0:
                    #     continue

                    # Now decode the contract function and its arguments
                    data = tx.input
                    method_id = data[0:10]
                    tx_from = getattr(tx, 'from')
                    if method_id == '0x47872b42':
                        function_name = 'unsealBid'
                        hash = '0x' + str(data[10:74])
                        value_str = '0x' + str(data[74:138])
                        value_in_wie = self.web3.toInt(hexstr=value_str)
                        value_in_ether = self.web3.fromWei(value_in_wie, 'ether')
                        salt = str(data[10:74])
                        self.logger.info('Method: ' + function_name + ' TxHash: ' + txHash + ' From: ' + str(tx_from) + ' BidHash: ' + hash + ' BidValue: ' + str(value_in_ether) + ' Salt: ' + salt)
                    elif method_id == '0xce92dced':
                        function_name = 'newBid'
                        self.logger.info('Method: '+ function_name + ' TxHash: ' + txHash + ' From: ' + str(tx_from))
                    elif method_id == '0xede8acdb':
                        function_name = 'startAuction'
                        self.logger.info('Method: '+ function_name + ' TxHash: ' + txHash + ' From: ' + str(tx_from))
                    elif method_id == '0xe27fe50f':
                        function_name = 'startAuctions'
                        self.logger.info('Method: '+ function_name + ' TxHash: ' + txHash + ' From: ' + str(tx_from))
                    elif method_id == '0xfebefd61':
                        function_name = 'startAuctionsAndBid'
                        self.logger.info('Method: '+ function_name + ' TxHash: ' + txHash + ' From: ' + str(tx_from))
                    elif method_id == '0x983b94fb':
                        function_name = 'finalizeAuction'
                        label_hash = '0x' + str(data[10:74])
                        self.logger.info('Method: ' + function_name + ' TxHash: ' + txHash + ' From: ' + str(tx_from) + ' BidHash: ' +label_hash)
                    elif method_id == '0x42966c68':
                        function_name = 'burn'
                        self.logger.info('Method: ' + function_name + ' TxHash: ' + txHash + ' From: ' + str(tx_from))
                    elif method_id == '0x4254b155':
                        function_name = 'register'
                        self.logger.info('Method: ' + function_name + ' TxHash: ' + txHash + ' From: ' + str(tx_from))
                    elif method_id == '0xcae9ca51':
                        function_name = 'approveAndCall'
                        self.logger.info('Method: ' + function_name + ' TxHash: ' + txHash + ' From: ' + str(tx_from))
                    elif method_id == '0xc1c8277f':
                        function_name = 'reclaimOwnership'
                        self.logger.info('Method: ' + function_name + ' TxHash: ' + txHash + ' From: ' + str(tx_from))
                    elif method_id == '0x0230a07c':
                        function_name = 'releaseDeed'
                        self.logger.info('Method: ' + function_name + ' TxHash: ' + txHash + ' From: ' + str(tx_from))
                    elif method_id == '0x79ce9fac':
                        function_name = 'transfer'
                        self.logger.info('Method: ' + function_name + ' TxHash: ' + txHash + ' From: ' + str(tx_from))
                    elif method_id == '0xa0fd20de':
                        function_name = 'newInstance'
                        self.logger.info('Method: ' + function_name + ' TxHash: ' + txHash + ' From: ' + str(tx_from))
                    elif method_id == '0xbeea7bfb':
                        function_name = 'newSubdomain'
                        self.logger.info('Method: ' + function_name + ' TxHash: ' + txHash + ' From: ' + str(tx_from))
                    elif method_id == '0x06ab5923':
                        function_name = 'setSubnodeOwner'
                        self.logger.info('Method: ' + function_name + ' TxHash: ' + txHash + ' From: ' + str(tx_from))
                    else:
                        self.logger.error('Method: '+ method_id + ' TxHash: '+ txHash + ' From: '+ str(tx_from))


