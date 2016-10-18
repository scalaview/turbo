
def Chile():
  return 135, 8


def purchase_cost(purchase_price, discount, count):
  return purchase_price * count * discount

def shipping_cost(shipping_cost_every_kg, kg, confirm):
  return kg * shipping_cost_every_kg + confirm

def shipping_cost_at_us(shipping_cost_every_kg, kg, confirm, rate):
  return shipping_cost(shipping_cost_every_kg, kg, confirm) / rate

def shipping_cost_kg_us(shipping_cost_every_kg, confirm, rate):
  return (shipping_cost_every_kg + confirm)/rate

def main():

  no_free_shipping_price = 1.74
  rate = 6.35
  count = 50
  purchase_price = 5
  discount = 1
  kg = 2.5
  shipping_cost_every_kg, confirm = Chile()
  profix = no_free_shipping_price * count * rate - purchase_cost(purchase_price, discount, count)

  free_shipping_price = (purchase_cost(purchase_price, discount, count) + shipping_cost(shipping_cost_every_kg, kg, confirm) + profix) /rate / 50

  print("rate: %s , count: %s, purchase_price: %s, discount: %s, kg: %s, shipping_cost: %s" % (rate, count, purchase_price, discount, kg, shipping_cost(shipping_cost_every_kg, kg, confirm)) )
  print("to set no_free_shipping_price: %s ,with shipping_cost: %s/kg" % (no_free_shipping_price, shipping_cost_kg_us(shipping_cost_every_kg, confirm, rate)))
  print("to set free shipping cost %s" % free_shipping_price)
  print("profix: %s yuan " % profix)

if __name__ == '__main__':
  main()