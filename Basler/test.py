from queue import Queue
q = Queue()
a = [1, 3, 4]
q.put(a)
a = [3, 4]
print(q.get())
