
class RunningAvg(object):
	running_started = False;
	avg = 0;
	count = 0;
	running_count = 0;
	mem = []
	def get(self, data):
		self.mem.append(data)
		data = float(data)

		if not self.running_started:
			self.avg = data
			self.running_started = True
		elif self.count < self.running_count:
			self.avg = (self.avg*self.count + data)/(self.count+1)
		else:
			self.avg = self.avg + data/self.running_count - self.mem[self.count - self.running_count]/self.running_count
		self.count += 1;
		return self.avg

	def __init__(self, newn=5):
		self.running_count = newn
		self.running_started = False
		self.avg = 0
		self.count = 0
		self.mem = []