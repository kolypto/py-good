all: performance.md

performance.dat: performance.py
	@./performance.py 5000 0 30 > performance.dat

IMAGES=performance-vps.png performance-time.png
$(IMAGES): performance.dat
	@./performance.gnuplot
performance.md: $(IMAGES)
	@true
