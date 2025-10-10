def create_multiplier(factor):
    # The inner function, which will be returned
    def multiplier(number):
        return number * factor
    return multiplier


double = create_multiplier(2)  # Creates a function that doubles its input
triple = create_multiplier(3)  # Creates a function that triples its input
a = 1
