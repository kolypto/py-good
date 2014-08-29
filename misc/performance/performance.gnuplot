#! /usr/bin/env gnuplot

# Plotting datasets:
# http://stackoverflow.com/questions/12818797/gnuplot-plotting-several-datasets-with-titles-from-one-file

reset
set terminal png size 800,600

set title "Performance comparison"
set key ins vert right top
set grid

set xlabel "Dictionary size"
set ylabel "validations/s"

# good (Invalid)
set style line 1 lc rgb "#00D000" linetype 0
# voluptuous (Invalid)
set style line 2 lc rgb "#0000D0" linetype 0
# good (Valid)
set style line 3 lc rgb "#00D000" lw 2
# voluptuous (Valid)
set style line 4 lc rgb "#0000D0" lw 2


# Plot multiple images
# do for [COL=2:5] {
#     outfile = sprintf('performance-%d.png', COL)
#     set output outfile
#     plot for [IDX=0:3] 'performance.dat' index IDX using 1:COL with lines ls IDX+1 title columnheader(1)
# }

# Plot multiple datasets, separated with '\n\n'
#plot for [IDX=0:3] 'performance.dat' index IDX using 1:2 with lines ls IDX+1 title columnheader(1)

# Plot multiple files

set output 'performance-time.png'
set ylabel "Execution Time, s"
set autoscale y
plot for [IDX=0:3] 'performance.dat' index IDX using 1:2 with lines ls IDX+1 title columnheader(1)

set output 'performance-vps.png'
set ylabel "Speed: Validations/s"
set logscale y
plot for [IDX=0:3] 'performance.dat' index IDX using 1:3 with lines ls IDX+1 title columnheader(1)
