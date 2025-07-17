import irig_h_gpio as irig

sender = irig.IrigHSender(sending_gpio_pin=6)

try:
    sender.start()
except KeyboardInterrupt:
    print('keyboard interrupt recieved. stopping...')
finally:
    sender.finish()