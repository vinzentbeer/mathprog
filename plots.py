import matplotlib.pyplot as plt

# Example data
x = range(20)  # e.g., input sizes or test cases
seq = [0.038,0.009,0.029,0.014,0.076,0.488,0.174,0.751,0.427,1.778,24.921,12.081,7.503,7.795,5.177,118.788,457.656,3600.074,437.75,3600.149]
scf = [0.041,0.006,0.039,0.03,0.055,0.077,0.18,0.254,0.159,0.406,5.609,3.855,2.329,2.28,5.617,9.304,54.283,57.565,155.011,1610.861]
mcf = [0.069,0.065,0.334,0.218,0.705,0.922,4.182,4.637,6.072,12.221,168.121,1179.32,3600.407,3600.414]

seq2 = [2.79, 1.52, 1.37, 1.24, 2.38, 1.98, 1.73, 2.51, 1.96, 3.99, 28.71, 16.59, 27.36, 28.23, 49.72, 163.19, 1691.26, 4865.90, 11016.17, 14206.49]
scf2 = [2.38, 1.78, 1.84, 1.46, 2.31, 1.84, 1.96, 2.32, 2.02, 2.28, 9.61, 8.58, 23.21, 22.68, 50.20, 55.35, 1305.21, 1296.87, 10684.42, 12135.13]
mcf2 = [1.97, 1.47, 1.80, 1.44, 2.53, 2.77, 5.06, 5.21, 7.29, 11.05, 90.93, 507.97, 3683.23, 3682.85]

colors = ['#1f77b4', '#2ca02c', '#d62728']

# Plotting the stats
plt.plot(x, seq2, marker='x', linestyle='-', label='SEQ', color=colors[0])
plt.plot(x, scf2, marker='o', linestyle='--', label='SCF', color=colors[1])
plt.plot(range(len(mcf2)), mcf2, marker='x', linestyle='-.', label='MCF', color=colors[2])

# Adding titles and labels
plt.title('Total runtime')
plt.xlabel('Instance')
plt.ylabel('Running Time [s]')

plt.yscale('log')

# Add grid and legend
plt.grid(True)
plt.legend()

# Show the plot
#plt.tight_layout()
plt.show()