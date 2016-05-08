import Quandl
import pandas as pd
from numpy import *
import statsmodels.api as sm
import matplotlib.pylab as plt
import plotly.graph_objs as go
import plotly as py
import cufflinks as cf
import datetime as dt
import seaborn as sns
from sklearn import linear_model
from plotly.offline import download_plotlyjs, init_notebook_mode, iplot
import scipy
import os


maturities = asarray([3, 6, 9, 12, 15, 18,21, 24, 30, 36, \
                     48, 60, 72, 84, 96, 108, 120])

beta_names = ['beta1', 'beta2', 'beta3']

def loadData():
	# load datasets + define parameters 
	lam_t = .0609

	# filter where we only get the last day of every month
	tau = ['Date', '1 MO',  '3 MO',  '6 MO',  '9 MO', '12 MO', '15 MO', '18 MO', '21 MO',  \
	               '24 MO', '30 MO', '36 MO', '48 MO', '60 MO', '72 MO', '84 MO', '96 MO', \
	               '108 MO', '120MO']

	__location__ = os.path.realpath(os.path.join(os.getcwd(), os.path.dirname(__file__)))
	loc = os.path.join(__location__ + '/Data/FBFitted.csv')
	ratedata = pd.read_csv(loc, index_col=0)

	_load2 = lambda x: (1.-exp(-lam_t*x)) / (lam_t*x)
	_load3 = lambda x: ((1.-exp(-lam_t*x)) / (lam_t*x)) - \
	exp(-lam_t*x)
	ratedata = ratedata.drop('1', axis=1)

	# convert ratedatea indices into datetiems
	ratedata.index = pd.to_datetime(ratedata.index, format='%Y%m%d')

	# Diebold and Li only use Jan 1980 to Dec 2000
	start_idx = ratedata.index.get_loc(dt.datetime.strptime('1985-01-31', '%Y-%m-%d'))
	ratedata = ratedata.iloc[start_idx:]

	# make 2D matrix of all of the beta coeff. for each maturity
	X = zeros((len(maturities), 2))
	# X[:,0] = sm.add_constant(ones(len(maturities)))
	X[:,0] = _load2(maturities)
	X[:,1] = _load3(maturities)
	X = sm.add_constant(X)

	# for each observation, fit the maturity curve 
	beta_fits = zeros((len(ratedata), 3))
	residuals = zeros((len(ratedata), 17))
	for i in range(0, len(ratedata)):
	    model = sm.regression.linear_model.OLS(ratedata.iloc[i], X)
	    results = model.fit()
	    beta_fits[i,:3] = results.params
	    residuals[i,:] = results.resid
	    
	# convert into a dataframe for conv. 
	beta_fits = pd.DataFrame(beta_fits, columns=beta_names)
	residuals = pd.DataFrame(residuals, columns=[str(mat) for mat in maturities])

	beta_fits.index = ratedata.index
	residuals.index = ratedata.index

	return beta_fits, residuals, ratedata


def table2(residuals):
	table2 = zeros((len(maturities), 9)) # initialize a matrix
	table2 = pd.DataFrame(table2, index=[str(mat) for mat in maturities])
	table2.columns = ['Mean', 'Std', 'Min', 'Max', 'MAE', 'RMSE', 'ACF(1)', 'ACF(12)', 'ACF(30)']
	for mat in maturities:
		table2.ix[str(mat), 0] = residuals.ix[:,str(mat)].mean()
		table2.ix[str(mat), 1] = residuals.ix[:,str(mat)].std()
		table2.ix[str(mat), 2] = residuals.ix[:,str(mat)].min()
		table2.ix[str(mat), 3] = residuals.ix[:,str(mat)].max()
		table2.ix[str(mat), 4] = abs(residuals.ix[:,str(mat)]).mean() # MAE
		table2.ix[str(mat), 5] = sqrt(pow(residuals.ix[:,str(mat)],2).mean())
		table2.ix[str(mat), 6] = sm.tsa.stattools.acf(residuals.ix[:,str(mat)], nlags=31)[1]
		table2.ix[str(mat), 7] = sm.tsa.stattools.acf(residuals.ix[:,str(mat)], nlags=31)[13]
		table2.ix[str(mat), 8] = sm.tsa.stattools.acf(residuals.ix[:,str(mat)], nlags=31)[-1]

	return table2


def table3(beta_fits):
	table3 = pd.DataFrame(zeros((3, 8)), index=beta_names)
	table3_columns = ['Mean', 'Std', 'Min', 'Max', 'ACF(1)', 'ACF(12)', 'ACF(30)', 'ADF']
	table3.columns = table3_columns
	for beta in beta_names:
		table3.ix[beta, 0] = beta_fits.ix[:,beta].mean()
		table3.ix[beta, 1] = beta_fits.ix[:,beta].std()
		table3.ix[beta, 2] = beta_fits.ix[:,beta].min()
		table3.ix[beta, 3] = beta_fits.ix[:,beta].max()
		table3.ix[beta, 4] = sm.tsa.stattools.acf(beta_fits.ix[:, beta], nlags=31)[1]
		table3.ix[beta, 5] = sm.tsa.stattools.acf(beta_fits.ix[:, beta], nlags=31)[13]
		table3.ix[beta, 6] = sm.tsa.stattools.acf(beta_fits.ix[:, beta], nlags=31)[-1]
		table3.ix[beta, -1] = sm.tsa.adfuller(beta_fits.ix[:,beta])[0] # note the ADF assumes [maxlag = 12*(nobs/100)^.25]

	return table3


def yieldContors(ratedata):

	data = [
	    go.Contour(
	        z = ratedata.as_matrix(),
	        x = ratedata.columns, 
	        y = ratedata.index)
	    ]

	layout = go.Layout(
	    title='Yields vs. Maturities',
	    width=640,
	    height=480,
	                xaxis=dict(
	                title='Maturity (months)',
	                titlefont=dict(
	                    size=16)
	                ),  
	            yaxis=dict(
	                title='Date',
	                titlefont=dict(
	                    size=16)
	                )


	    )

	fig = go.Figure(data=data, layout=layout)

	return fig


def exampleYield(ratedata, loc):
	if type(loc) != list:
		print('You must input a list')

	if len(loc) ==1:
		tit = str(ratedata.index[loc[0]])
	else:
		tit = "Sample Yield Curves"
	layout = go.Layout(
            width=640,
            height=480,
            title=tit,
            titlefont=dict(
                size=24),
    
            xaxis=dict(
                title='Maturity (months)',
                titlefont=dict(
                    size=20)
                ),  
            yaxis=dict(
                title='Yield (percent)',
                titlefont=dict(
                    size=20)
                ),
        
            legend=dict(
                font=dict(
                    size=12))

                )
            
	return ratedata.iloc[loc,:].transpose().iplot(kind='scatter', layout=layout)


def beta_resid(residuals):
	resid_interest = residuals.ix[:,['3','6', '12', '24', '60', '120']]
	layout = go.Layout(
				title='Residuals for selected maturities (months)',
	            titlefont=dict(
	                size=18),
	            legend= dict(
	                font=dict(
	                    size=16)),
	#             title='Residuals for selected maturity periods',
	            width=640,
	            height=480,
	            )
	return resid_interest.iplot(subplots=True, \
		title='Residuals for selected maturity periods', layout=layout)



def beta_dist(beta_fits):
	fig, axes = plt.subplots(1,3, figsize=(10,7))
	fig.suptitle('Fitted Parameters Histogram')
	sns.set(font_scale=1)
	d = sns.distplot(beta_fits.ix[:,'beta1'], ax=axes[0])
	d = sns.distplot(beta_fits.ix[:,'beta2'], ax=axes[1])
	d = sns.distplot(beta_fits.ix[:,'beta3'], ax=axes[2])

	return fig


def fig7(ratedata, beta_fits):
	beta1_hat = ratedata.ix[:, '120']
	beta2_hat = ratedata.ix[:,'120'] - ratedata.ix[:,'3']
	beta3_hat = 2*ratedata.ix[:,'24'] - \
		(ratedata.ix[:,'120'] + ratedata.ix[:,'3'])

	layout = go.Layout(
				title='Residuals for selected maturities (months)',
	            titlefont=dict(
	                size=18),
	            legend= dict(
	                font=dict(
	                    size=16)),
	#             title='Residuals for selected maturity periods',
	            width=640,
	            height=480,
	            )


	fig = py.tools.make_subplots(rows=3, 
		shared_xaxes=True, print_grid=False,subplot_titles=(
			'Level', 'Slope', 'Curvature' ))

	beta1a = go.Scatter(
			x = beta1_hat.index, 
			y = beta1_hat, 
			name = 'Emprical')

	beta1b = go.Scatter(
			x = beta_fits.index,
			y = beta_fits.ix[:,'beta1'], 
			name='Fitted')

	beta2a = go.Scatter(
			x = beta2_hat.index, 
			y = beta2_hat, 
			name = 'Emprical')

	beta2b = go.Scatter(
			x = beta_fits.index,
			y = -beta_fits.ix[:,'beta2'], 
			name='Fitted')

	beta3a = go.Scatter(
			x = beta3_hat.index, 
			y = beta3_hat, 
			name = 'Emprical')

	beta3b = go.Scatter(
			x = beta_fits.index,
			y = .3*beta_fits.ix[:,'beta3'], 
			name='Fitted')

	fig.append_trace(beta1a,1,1)
	fig.append_trace(beta1b, 1,1)

	fig.append_trace(beta2a,2,1)
	fig.append_trace(beta2b, 2,1)

	fig.append_trace(beta3a,3,1)
	fig.append_trace(beta3b, 3,1)

	return fig
































