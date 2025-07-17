import irig_h_gpio as irig

sender = irig.IrigHSender(6)

try:
    sender.start()
except KeyboardInterrupt:
    print('keyboard interrupt recieved. stopping...')
finally:
    sender.finish()