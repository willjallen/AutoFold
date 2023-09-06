from strategy import Strategy

class ExampleStrategy(Strategy):
   def __init__(self):
       super().__init__(name=__name__) 
       
       