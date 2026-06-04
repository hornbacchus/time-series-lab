namespace TSL.AddIn
{
    /// <summary>
    /// Generates the Ribbon XML for the "Time Series Lab" tab.
    /// </summary>
    public static class RibbonXml
    {
        public static string GetXml()
        {
            return @"
<customUI xmlns='http://schemas.microsoft.com/office/2009/07/customui'
         xmlns:tsl='TimeSeriesLab'
         onLoad='OnRibbonLoad'>
  <ribbon>
    <tabs>
      <tab idQ='tsl:tslTab' label='Time Series Lab'>

        <group id='grpQuickActions' label='Techniques'>
          <!-- Multivariate / system modeling (the core macro-strategist toolkit). -->
          <button id='btnVar'
                  label='VAR'
                  size='large'
                  imageMso='ChartTypeColumnInsertGallery'
                  onAction='OnVar'
                  screentip='Vector Autoregression (VAR)'
                  supertip='Fit a Vector Autoregression to a system of time series. Produces impulse-response functions, variance decompositions, and forecasts for each variable. The quintessential macro modeling tool.' />
          <button id='btnPca'
                  label='PCA'
                  size='large'
                  imageMso='ChartTrendline'
                  onAction='OnPcaAnalysis'
                  screentip='Principal Component Analysis (PCA)'
                  supertip='Reduce a set of correlated time series into a smaller number of uncorrelated principal components. Canonical use: level/slope/curvature decomposition of a yield curve.' />
          <button id='btnDfm'
                  label='DFM'
                  size='large'
                  imageMso='ChartLines'
                  onAction='OnDynamicFactorModel'
                  screentip='Dynamic Factor Model (DFM)'
                  supertip='Extract common latent factors that drive multiple time series jointly. The nowcasting backbone of Fed GDPNow, NY Fed Nowcast, and Chicago Fed CFNAI.' />
          <button id='btnCointegration'
                  label='Cointegration'
                  size='large'
                  imageMso='ChartTypeLineInsertGallery'
                  onAction='OnCointegration'
                  screentip='Johansen Cointegration + VECM'
                  supertip='Test for long-run equilibrium relationships among multiple non-stationary series and fit a Vector Error Correction Model. Used for term-structure, PPP, and commodity-currency trading signals.' />
          <separator id='sepQA1' />
          <!-- Univariate workhorses + causality/forecasting. -->
          <button id='btnGranger'
                  label='Granger'
                  size='large'
                  imageMso='ChartRadarChart'
                  onAction='OnGrangerCausality'
                  screentip='Granger Causality Test'
                  supertip='Test whether one time series helps predict another. The foundation of lead-lag screening (does oil lead CPI? does the curve lead recession?).' />
          <button id='btnRollingCcf'
                  label='Rolling CCF'
                  size='large'
                  imageMso='AutoSum'
                  onAction='OnRollingCcf'
                  screentip='Rolling Cross-Correlation Lag'
                  supertip='Time-varying lead-lag analysis over a moving window. Surfaces when a stable lead-lag relationship (VIX leading credit, PMI leading GDP) changes regime.' />
          <button id='btnSeasonalAdj'
                  label='Seasonal Adj'
                  size='large'
                  imageMso='ChartAreaChart'
                  onAction='OnSeasonalAdjustment'
                  screentip='Seasonal Adjustment (STL)'
                  supertip='Decompose a time series into trend, seasonal, and remainder components using STL. Use X-13 ARIMA-SEATS via the Technique Explorer for the BLS/BEA gold standard.' />
          <button id='btnForecast'
                  label='Forecast'
                  size='large'
                  imageMso='ChartTypeAreaInsertGallery'
                  onAction='OnForecast'
                  screentip='Auto ARIMA Forecast'
                  supertip='Generate forecasts with prediction intervals using automatic ARIMA model selection. The workhorse univariate baseline.' />
          <button id='btnProphet'
                  label='Prophet'
                  size='large'
                  imageMso='Refresh'
                  onAction='OnProphet'
                  screentip='Prophet Forecast'
                  supertip='Forecasting with built-in trend, multiple seasonalities, and explicit holiday effects. Meta/Facebook&apos;s default for series with calendar-driven patterns.' />
          <button id='btnConformal'
                  label='Conformal'
                  size='large'
                  imageMso='ControlProperties'
                  onAction='OnConformal'
                  screentip='Conformal Prediction Intervals'
                  supertip='Calibrated, distribution-free forecast intervals. Produces valid prediction bands that hold regardless of model misspecification — answers &quot;75% probability CPI prints between X and Y&quot; without parametric assumptions.' />
          <separator id='sepQA2' />
          <!-- Regime / volatility / state-space. -->
          <button id='btnMarkovSwitch'
                  label='Regime Switch'
                  size='large'
                  imageMso='TracePrecedents'
                  onAction='OnMarkovSwitching'
                  screentip='Markov Switching Model'
                  supertip='Fit a Markov-switching model to detect regime changes (recession vs expansion, high-vol vs low-vol, hawkish vs dovish). Outputs regime probabilities over time.' />
          <button id='btnChangePoint'
                  label='Change Point'
                  size='large'
                  imageMso='ReviewAcceptChange'
                  onAction='OnChangePoint'
                  screentip='PELT Change Point Detection'
                  supertip='Detect structural breaks in a time series using the PELT algorithm. Locates when the underlying process shifted (policy regime, trade regime, supply chain, etc.).' />
          <button id='btnGarch'
                  label='GARCH'
                  size='large'
                  imageMso='ChartInsert'
                  onAction='OnGarch'
                  screentip='GARCH Volatility Model'
                  supertip='Fit a GARCH(1,1) model to capture volatility clustering in a return series. Basis for VaR, risk budgeting, and volatility regime analysis.' />
          <button id='btnKalman'
                  label='Structural TS'
                  size='large'
                  imageMso='FunctionWizard'
                  onAction='OnStructuralTS'
                  screentip='Structural Time Series (UCM)'
                  supertip='Fit an Unobserved Components Model that decomposes the series into level, trend, seasonal, and cycle components via Kalman filtering. Used for signal extraction, nowcasting, and structural decomposition (output gap, NAIRU, neutral rate r*).' />
        </group>

        <!-- Bespoke: packaged, end-to-end bespoke analyses (vs the generic
             statistical techniques in the Techniques group). Trails Techniques;
             grows case-by-case as future packaged analyses are added. A single
             member today (Bond Yield Forecast) is the intended state. -->
        <group id='grpBespoke' label='Bespoke'>
          <!-- Bond Yield Forecast (GAP-1 routing fix): a MENU, not a split
               button. The top portion opens the dropdown; the two items are
               'Open Input Template' and 'Run Bond Yield Forecast' (the one-shot
               OnBondYieldForecastRun, which auto-injects the active workbook
               path). Dropped the former split-button primary action: it did not
               fire reliably (top-portion click no-op) and duplicated the
               dropdown Run — a single, obvious run path is clearer and aligns
               with the documented 'Bond Yield Forecast -> Run Bond Yield
               Forecast' trigger. Modeled on the menuRecommender pattern below. -->
          <menu id='menuBondYieldForecast'
                label='Bond Yield Forecast'
                size='large'
                imageMso='ChartTypeLineInsertGallery'
                screentip='Bond Yield Forecast (BVAR-SV)'
                supertip='Large Bayesian VAR with stochastic volatility for U.S. Treasury yield curve forecasting, conditioned on economist macro projections. Requires a 3-sheet bundled .xlsx workbook (BondYield_Macro / BondYield_Yields / BondYield_Projections). Use &apos;Open Input Template&apos; to generate a starter workbook, edit + save it, then &apos;Run Bond Yield Forecast&apos;.'>
            <button id='btnBondYieldOpenTemplate'
                    label='Open Input Template'
                    imageMso='TableInsertExcel'
                    onAction='OnBondYieldForecastOpenTemplate'
                    screentip='Open the Bond Yield Forecast input template'
                    supertip='Opens a pre-formatted .xlsx with example macro/yield/projection data. Edit the data sheets in place, save the workbook, then click &apos;Run Bond Yield Forecast&apos; to forecast.' />
            <button id='btnBondYieldRun'
                    label='Run Bond Yield Forecast'
                    imageMso='MacroPlay'
                    onAction='OnBondYieldForecastRun'
                    screentip='Run the BVAR-SV forecast on the active workbook'
                    supertip='Dispatches the BVAR-SV estimation + conditional forecast pipeline against the saved active workbook (one-shot: auto-injects the workbook path). Results render on a new &quot;Bond Yield Forecast Results&quot; sheet; diagnostics on a &quot;Bond Yield Forecast Audit&quot; sheet. Estimation typically takes 15-30 seconds on the canonical fixture.' />
          </menu>
        </group>

        <group id='grpExplore' label='Explore'>
          <splitButton id='sbExplorer' size='large'>
            <button id='btnExplorer'
                    label='Technique Explorer'
                    imageMso='FindDialog'
                    onAction='OnTechniqueExplorer'
                    screentip='Technique Explorer'
                    supertip='Browse all 79 techniques. Click the arrow to jump to a category.' />
            <menu id='menuExplorerCategories'>
              <button id='btnCatDecomp' label='Decomposition &amp; Seasonal' imageMso='ChartAreaChart' onAction='OnExplorerCategory' tag='Decomposition &amp; Seasonal Adjustment' />
              <button id='btnCatForecast' label='Forecasting (Classical)' imageMso='ChartTypeAreaInsertGallery' onAction='OnExplorerCategory' tag='Forecasting (Classical)' />
              <button id='btnCatStation' label='Stationarity / Tests' imageMso='FunctionWizard' onAction='OnExplorerCategory' tag='Stationarity / Tests' />
              <button id='btnCatMulti' label='Multivariate Systems' imageMso='ChartRadarChart' onAction='OnExplorerCategory' tag='Multivariate Systems' />
              <button id='btnCatState' label='State Space / Filtering' imageMso='ChartTypeLineInsertGallery' onAction='OnExplorerCategory' tag='State Space / Filtering' />
              <button id='btnCatRegime' label='Regimes / Nonlinear' imageMso='TracePrecedents' onAction='OnExplorerCategory' tag='Regimes / Nonlinear' />
              <menuSeparator id='sepCat1' />
              <button id='btnCatVol' label='Volatility / Risk / Tails' imageMso='ChartInsert' onAction='OnExplorerCategory' tag='Volatility / Risk / Tails' />
              <button id='btnCatFreq' label='Frequency Domain / Signal' imageMso='Refresh' onAction='OnExplorerCategory' tag='Frequency Domain / Signal' />
              <button id='btnCatChange' label='Change Points / Anomalies' imageMso='ReviewAcceptChange' onAction='OnExplorerCategory' tag='Change Points / Anomalies / Interventions' />
              <button id='btnCatCausal' label='Causality / Lead-Lag' imageMso='AutoSum' onAction='OnExplorerCategory' tag='Causality / Relationships / Lead-Lag' />
              <menuSeparator id='sepCat2' />
              <button id='btnCatEval' label='Evaluation / Uncertainty' imageMso='ControlProperties' onAction='OnExplorerCategory' tag='Evaluation / Uncertainty' />
              <button id='btnCatMissing' label='Missing Data' imageMso='RecordsDeleteRecord' onAction='OnExplorerCategory' tag='Missing Data / Temporal Disaggregation' />
              <button id='btnCatML' label='ML / Deep Learning' imageMso='MacroPlay' onAction='OnExplorerCategory' tag='ML / Deep Learning' />
              <menuSeparator id='sepCat3' />
              <button id='btnCatAll' label='Show All Categories' imageMso='FindDialog' onAction='OnTechniqueExplorer' />
            </menu>
          </splitButton>
          <menu id='menuRecommender'
                label='Recommender'
                size='large'
                imageMso='AutoSum'
                screentip='Recommender Wizard'
                supertip='Choose an analysis goal to get technique recommendations, or open the full wizard.'>
            <button id='btnRecForecast' label='Forecast future values' imageMso='ChartTypeAreaInsertGallery' onAction='OnRecommenderGoal' tag='forecast' />
            <button id='btnRecDescribe' label='Describe / decompose the series' imageMso='ChartAreaChart' onAction='OnRecommenderGoal' tag='describe' />
            <button id='btnRecAnomaly' label='Detect anomalies / outliers' imageMso='TracePrecedents' onAction='OnRecommenderGoal' tag='anomaly' />
            <button id='btnRecCausality' label='Test causality / relationships' imageMso='ChartRadarChart' onAction='OnRecommenderGoal' tag='causality' />
            <button id='btnRecRelation' label='Explore relationships' imageMso='ChartTypeLineInsertGallery' onAction='OnRecommenderGoal' tag='relationship' />
            <button id='btnRecTesting' label='Statistical testing' imageMso='FunctionWizard' onAction='OnRecommenderGoal' tag='test' />
            <menuSeparator id='sepRecWizard' />
            <button id='btnRecFullWizard' label='Open full wizard...' imageMso='AutoSum' onAction='OnRecommenderWizard' />
          </menu>
          <button id='btnReadiness'
                  label='Data Readiness'
                  size='large'
                  imageMso='ReviewAcceptChange'
                  onAction='OnDataReadiness'
                  screentip='Data Readiness Score'
                  supertip='Check your selected data for quality issues before analysis.' />
        </group>

        <group id='grpRun' label='Run'>
          <menu id='menuPreset'
                getLabel='OnPresetGetLabel'
                size='large'
                imageMso='ControlProperties'
                screentip='Analysis Preset'
                supertip='Fast: quick results. Balanced: good defaults with cross-validation. Thorough: extensive search, manual recompute.'>
            <toggleButton id='btnPresetFast'
                          label='Fast'
                          tag='Fast'
                          getPressed='OnPresetGetPressed'
                          onAction='OnPresetMenuClick'
                          screentip='Fast Preset'
                          supertip='Quick results with minimal cross-validation. Best for exploratory work.' />
            <toggleButton id='btnPresetBalanced'
                          label='Balanced'
                          tag='Balanced'
                          getPressed='OnPresetGetPressed'
                          onAction='OnPresetMenuClick'
                          screentip='Balanced Preset (default)'
                          supertip='Sensible defaults with cross-validation. The right choice for most analyses.' />
            <toggleButton id='btnPresetThorough'
                          label='Thorough'
                          tag='Thorough'
                          getPressed='OnPresetGetPressed'
                          onAction='OnPresetMenuClick'
                          screentip='Thorough Preset'
                          supertip='Extensive model search and cross-validation. Slower; manual re-run required for THOROUGH formulas.' />
          </menu>
          <separator id='sepRun0' />
          <button id='btnRun'
                  label='Run'
                  size='large'
                  imageMso='MacroPlay'
                  onAction='OnRun'
                  screentip='Run Analysis'
                  supertip='Execute the currently configured technique from the Task Pane.' />
          <button id='btnCancel'
                  label='Cancel'
                  size='large'
                  imageMso='RecordsDeleteRecord'
                  onAction='OnCancel'
                  screentip='Cancel'
                  supertip='Immediately stop the current computation.' />
          <button id='btnRerunThorough'
                  label='Re-run Thorough'
                  size='large'
                  imageMso='Refresh'
                  onAction='OnRerunThorough'
                  screentip='Re-run Thorough Formulas'
                  supertip='Increment the trigger token to force all THOROUGH formulas in this workbook to recompute.' />
          <separator id='sepRun2' />
          <button id='btnSettings'
                  label='Settings'
                  size='large'
                  imageMso='ControlProperties'
                  onAction='OnSettings'
                  screentip='Settings'
                  supertip='Configure Time Series Lab preferences.' />
        </group>

        <group id='grpHelp' label='Help'>
          <button id='btnUdfGuide'
                  label='UDF Formula Guide'
                  size='large'
                  imageMso='FunctionWizard'
                  onAction='OnUdfGuide'
                  screentip='UDF Formula Guide'
                  supertip='Browse available worksheet functions with examples and a formula builder.' />
          <splitButton id='sbUserGuide' size='large'>
            <button id='btnUserGuide'
                    label='User Guide'
                    imageMso='Help'
                    onAction='OnOpenUserGuideHtml'
                    screentip='User Guide'
                    supertip='Open the Time Series Lab User Guide in your browser.' />
            <menu id='menuUserGuide'>
              <button id='btnGuideHtml'
                      label='Open as Web Page'
                      imageMso='HyperlinkInsert'
                      onAction='OnOpenUserGuideHtml'
                      screentip='Web Page'
                      supertip='Open the User Guide as an HTML page in your browser.' />
              <button id='btnGuideWord'
                      label='Open as Word Document'
                      imageMso='FileSaveAsWordDocx'
                      onAction='OnOpenUserGuide'
                      screentip='Word Document'
                      supertip='Open the User Guide as a Word document (.docx).' />
            </menu>
          </splitButton>
          <splitButton id='sbSampleData' size='large'>
            <button id='btnSampleData'
                    label='Sample Data'
                    imageMso='TableInsertExcel'
                    onAction='OnSampleDataTreasury'
                    screentip='Sample Data'
                    supertip='Open an example dataset in a new worksheet.' />
            <menu id='menuSampleData'>
              <menu id='menuSample_decomp' label='Decomposition &amp; Seasonal Adjustment'>
                <button id='btnSample_stl_decompose'
                        label='STL Data: Airline Passengers (Monthly 1949-60)'
                        imageMso='TableInsertExcel'
                        onAction='OnSampleDataByTechnique'
                        tag='stl_decompose'
                        screentip='Sample data for STL Decomposition'
                        supertip='Load a representative sample dataset for the STL Decomposition technique. Dataset: Airline Passengers (Monthly 1949-60). Each technique&apos;s sample was chosen to be a canonical or otherwise appropriate input. This is the same data you can use with the technique&apos;s Quick Action button or by selecting it in the Technique Explorer.' />
                <button id='btnSample_classical_decompose'
                        label='Classical Decomp Data: Airline Passengers (Monthly 1949-60)'
                        imageMso='TableInsertExcel'
                        onAction='OnSampleDataByTechnique'
                        tag='classical_decompose'
                        screentip='Sample data for Classical Decomposition'
                        supertip='Load a representative sample dataset for the Classical Decomposition technique. Dataset: Airline Passengers (Monthly 1949-60). Each technique&apos;s sample was chosen to be a canonical or otherwise appropriate input. This is the same data you can use with the technique&apos;s Quick Action button or by selecting it in the Technique Explorer.' />
                <button id='btnSample_mstl_decompose'
                        label='MSTL Data: Airline Passengers (Monthly 1949-60)'
                        imageMso='TableInsertExcel'
                        onAction='OnSampleDataByTechnique'
                        tag='mstl_decompose'
                        screentip='Sample data for MSTL Decomposition'
                        supertip='Load a representative sample dataset for the MSTL Decomposition technique. Dataset: Airline Passengers (Monthly 1949-60). Each technique&apos;s sample was chosen to be a canonical or otherwise appropriate input. This is the same data you can use with the technique&apos;s Quick Action button or by selecting it in the Technique Explorer.' />
                <button id='btnSample_x13_seasonal_adjust'
                        label='X-13 Data: Nonfarm Payrolls NSA (Monthly 1939-present)'
                        imageMso='TableInsertExcel'
                        onAction='OnSampleDataByTechnique'
                        tag='x13_seasonal_adjust'
                        screentip='Sample data for X-13 ARIMA-SEATS'
                        supertip='Load a representative sample dataset for the X-13 ARIMA-SEATS technique. Dataset: Nonfarm Payrolls NSA (Monthly 1939-present). Each technique&apos;s sample was chosen to be a canonical or otherwise appropriate input. This is the same data you can use with the technique&apos;s Quick Action button or by selecting it in the Technique Explorer.' />
              </menu>
              <menu id='menuSample_fcst' label='Forecasting (Classical)'>
                <button id='btnSample_ets_hw'
                        label='ETS / Holt-Winters Data: Airline Passengers (Monthly 1949-60)'
                        imageMso='TableInsertExcel'
                        onAction='OnSampleDataByTechnique'
                        tag='ets_hw'
                        screentip='Sample data for ETS / Holt-Winters'
                        supertip='Load a representative sample dataset for the ETS / Holt-Winters technique. Dataset: Airline Passengers (Monthly 1949-60). Each technique&apos;s sample was chosen to be a canonical or otherwise appropriate input. This is the same data you can use with the technique&apos;s Quick Action button or by selecting it in the Technique Explorer.' />
                <button id='btnSample_theta_forecast'
                        label='Theta Data: Airline Passengers (Monthly 1949-60)'
                        imageMso='TableInsertExcel'
                        onAction='OnSampleDataByTechnique'
                        tag='theta_forecast'
                        screentip='Sample data for Theta Method'
                        supertip='Load a representative sample dataset for the Theta Method technique. Dataset: Airline Passengers (Monthly 1949-60). Each technique&apos;s sample was chosen to be a canonical or otherwise appropriate input. This is the same data you can use with the technique&apos;s Quick Action button or by selecting it in the Technique Explorer.' />
                <button id='btnSample_arima'
                        label='ARIMA Data: US Real GDP Growth (Quarterly SAAR)'
                        imageMso='TableInsertExcel'
                        onAction='OnSampleDataByTechnique'
                        tag='arima'
                        screentip='Sample data for ARIMA'
                        supertip='Load a representative sample dataset for the ARIMA technique. Dataset: US Real GDP Growth (Quarterly SAAR). Each technique&apos;s sample was chosen to be a canonical or otherwise appropriate input. This is the same data you can use with the technique&apos;s Quick Action button or by selecting it in the Technique Explorer.' />
                <button id='btnSample_sarima'
                        label='SARIMA Data: Airline Passengers (Monthly 1949-60)'
                        imageMso='TableInsertExcel'
                        onAction='OnSampleDataByTechnique'
                        tag='sarima'
                        screentip='Sample data for SARIMA'
                        supertip='Load a representative sample dataset for the SARIMA technique. Dataset: Airline Passengers (Monthly 1949-60). Each technique&apos;s sample was chosen to be a canonical or otherwise appropriate input. This is the same data you can use with the technique&apos;s Quick Action button or by selecting it in the Technique Explorer.' />
                <button id='btnSample_auto_arima'
                        label='Auto ARIMA Data: Airline Passengers (Monthly 1949-60)'
                        imageMso='TableInsertExcel'
                        onAction='OnSampleDataByTechnique'
                        tag='auto_arima'
                        screentip='Sample data for Auto ARIMA'
                        supertip='Load a representative sample dataset for the Auto ARIMA technique. Dataset: Airline Passengers (Monthly 1949-60). Each technique&apos;s sample was chosen to be a canonical or otherwise appropriate input. This is the same data you can use with the technique&apos;s Quick Action button or by selecting it in the Technique Explorer.' />
                <button id='btnSample_arimax_sarimax'
                        label='ARIMAX/SARIMAX Data: US Macro Quarterly (GDP, CPI, FF, UNRATE)'
                        imageMso='TableInsertExcel'
                        onAction='OnSampleDataByTechnique'
                        tag='arimax_sarimax'
                        screentip='Sample data for ARIMAX / SARIMAX'
                        supertip='Load a representative sample dataset for the ARIMAX / SARIMAX technique. Dataset: US Macro Quarterly (GDP, CPI, FF, UNRATE). Each technique&apos;s sample was chosen to be a canonical or otherwise appropriate input. This is the same data you can use with the technique&apos;s Quick Action button or by selecting it in the Technique Explorer.' />
                <button id='btnSample_transfer_function'
                        label='Transfer Function Data: US Macro Quarterly (GDP, CPI, FF, UNRATE)'
                        imageMso='TableInsertExcel'
                        onAction='OnSampleDataByTechnique'
                        tag='transfer_function'
                        screentip='Sample data for Transfer Function Model'
                        supertip='Load a representative sample dataset for the Transfer Function Model technique. Dataset: US Macro Quarterly (GDP, CPI, FF, UNRATE). Each technique&apos;s sample was chosen to be a canonical or otherwise appropriate input. This is the same data you can use with the technique&apos;s Quick Action button or by selecting it in the Technique Explorer.' />
                <button id='btnSample_intermittent_demand'
                        label='Intermittent Demand Data: Intermittent Demand Series (Monthly, 70% zero)'
                        imageMso='TableInsertExcel'
                        onAction='OnSampleDataByTechnique'
                        tag='intermittent_demand'
                        screentip='Sample data for Intermittent Demand Forecasting'
                        supertip='Load a representative sample dataset for the Intermittent Demand Forecasting technique. Dataset: Intermittent Demand Series (Monthly, 70% zero). Each technique&apos;s sample was chosen to be a canonical or otherwise appropriate input. This is the same data you can use with the technique&apos;s Quick Action button or by selecting it in the Technique Explorer.' />
              </menu>
              <menu id='menuSample_stat' label='Stationarity / Tests'>
                <button id='btnSample_adf_test'
                        label='ADF Data: US Real GDP Growth (Quarterly SAAR)'
                        imageMso='TableInsertExcel'
                        onAction='OnSampleDataByTechnique'
                        tag='adf_test'
                        screentip='Sample data for Augmented Dickey-Fuller Test'
                        supertip='Load a representative sample dataset for the Augmented Dickey-Fuller Test technique. Dataset: US Real GDP Growth (Quarterly SAAR). Each technique&apos;s sample was chosen to be a canonical or otherwise appropriate input. This is the same data you can use with the technique&apos;s Quick Action button or by selecting it in the Technique Explorer.' />
                <button id='btnSample_kpss_test'
                        label='KPSS Data: US Real GDP Growth (Quarterly SAAR)'
                        imageMso='TableInsertExcel'
                        onAction='OnSampleDataByTechnique'
                        tag='kpss_test'
                        screentip='Sample data for KPSS Test'
                        supertip='Load a representative sample dataset for the KPSS Test technique. Dataset: US Real GDP Growth (Quarterly SAAR). Each technique&apos;s sample was chosen to be a canonical or otherwise appropriate input. This is the same data you can use with the technique&apos;s Quick Action button or by selecting it in the Technique Explorer.' />
                <button id='btnSample_pp_test'
                        label='Phillips-Perron Data: US Real GDP Growth (Quarterly SAAR)'
                        imageMso='TableInsertExcel'
                        onAction='OnSampleDataByTechnique'
                        tag='pp_test'
                        screentip='Sample data for Phillips-Perron Test'
                        supertip='Load a representative sample dataset for the Phillips-Perron Test technique. Dataset: US Real GDP Growth (Quarterly SAAR). Each technique&apos;s sample was chosen to be a canonical or otherwise appropriate input. This is the same data you can use with the technique&apos;s Quick Action button or by selecting it in the Technique Explorer.' />
              </menu>
              <menu id='menuSample_mvar' label='Multivariate Systems'>
                <button id='btnSample_var'
                        label='VAR Data: US Macro Quarterly (GDP, CPI, FF, UNRATE)'
                        imageMso='TableInsertExcel'
                        onAction='OnSampleDataByTechnique'
                        tag='var'
                        screentip='Sample data for Vector Autoregression (VAR)'
                        supertip='Load a representative sample dataset for the Vector Autoregression (VAR) technique. Dataset: US Macro Quarterly (GDP, CPI, FF, UNRATE). Each technique&apos;s sample was chosen to be a canonical or otherwise appropriate input. This is the same data you can use with the technique&apos;s Quick Action button or by selecting it in the Technique Explorer.' />
                <button id='btnSample_vecm'
                        label='VECM Data: UST 2Y/5Y/10Y/30Y Yields (Daily)'
                        imageMso='TableInsertExcel'
                        onAction='OnSampleDataByTechnique'
                        tag='vecm'
                        screentip='Sample data for Vector Error Correction Model (VECM)'
                        supertip='Load a representative sample dataset for the Vector Error Correction Model (VECM) technique. Dataset: UST 2Y/5Y/10Y/30Y Yields (Daily). Each technique&apos;s sample was chosen to be a canonical or otherwise appropriate input. This is the same data you can use with the technique&apos;s Quick Action button or by selecting it in the Technique Explorer.' />
                <button id='btnSample_johansen_cointegration'
                        label='Johansen Data: UST 2Y/5Y/10Y/30Y Yields (Daily)'
                        imageMso='TableInsertExcel'
                        onAction='OnSampleDataByTechnique'
                        tag='johansen_cointegration'
                        screentip='Sample data for Johansen Cointegration Test'
                        supertip='Load a representative sample dataset for the Johansen Cointegration Test technique. Dataset: UST 2Y/5Y/10Y/30Y Yields (Daily). Each technique&apos;s sample was chosen to be a canonical or otherwise appropriate input. This is the same data you can use with the technique&apos;s Quick Action button or by selecting it in the Technique Explorer.' />
                <button id='btnSample_bvar'
                        label='Bayesian VAR Data: US Macro Quarterly (GDP, CPI, FF, UNRATE)'
                        imageMso='TableInsertExcel'
                        onAction='OnSampleDataByTechnique'
                        tag='bvar'
                        screentip='Sample data for Bayesian VAR'
                        supertip='Load a representative sample dataset for the Bayesian VAR technique. Dataset: US Macro Quarterly (GDP, CPI, FF, UNRATE). Each technique&apos;s sample was chosen to be a canonical or otherwise appropriate input. This is the same data you can use with the technique&apos;s Quick Action button or by selecting it in the Technique Explorer.' />
                <button id='btnSample_dynamic_factor_model'
                        label='DFM Data: Stock-Watson Coincident Indicators (Monthly)'
                        imageMso='TableInsertExcel'
                        onAction='OnSampleDataByTechnique'
                        tag='dynamic_factor_model'
                        screentip='Sample data for Dynamic Factor Model'
                        supertip='Load a representative sample dataset for the Dynamic Factor Model technique. Dataset: Stock-Watson Coincident Indicators (Monthly). Each technique&apos;s sample was chosen to be a canonical or otherwise appropriate input. This is the same data you can use with the technique&apos;s Quick Action button or by selecting it in the Technique Explorer.' />
                <button id='btnSample_pca_analysis'
                        label='PCA Data: UST 2Y/5Y/10Y/30Y Yields (Daily)'
                        imageMso='TableInsertExcel'
                        onAction='OnSampleDataByTechnique'
                        tag='pca_analysis'
                        screentip='Sample data for Principal Component Analysis'
                        supertip='Load a representative sample dataset for the Principal Component Analysis technique. Dataset: UST 2Y/5Y/10Y/30Y Yields (Daily). Each technique&apos;s sample was chosen to be a canonical or otherwise appropriate input. This is the same data you can use with the technique&apos;s Quick Action button or by selecting it in the Technique Explorer.' />
                <button id='btnSample_forecast_reconciliation'
                        label='Forecast Reconciliation Data: US Macro Quarterly (GDP, CPI, FF, UNRATE)'
                        imageMso='TableInsertExcel'
                        onAction='OnSampleDataByTechnique'
                        tag='forecast_reconciliation'
                        screentip='Sample data for Hierarchical Forecast Reconciliation'
                        supertip='Load a representative sample dataset for the Hierarchical Forecast Reconciliation technique. Dataset: US Macro Quarterly (GDP, CPI, FF, UNRATE). Each technique&apos;s sample was chosen to be a canonical or otherwise appropriate input. This is the same data you can use with the technique&apos;s Quick Action button or by selecting it in the Technique Explorer.' />
              </menu>
              <menu id='menuSample_state' label='State Space / Filtering'>
                <button id='btnSample_kalman_filter'
                        label='Structural TS Data: Nile River Annual Flow (1871-1970)'
                        imageMso='TableInsertExcel'
                        onAction='OnSampleDataByTechnique'
                        tag='structural_ts'
                        screentip='Sample data for Structural Time Series (UCM)'
                        supertip='Load a representative sample dataset for the Structural Time Series (UCM) technique. Dataset: Nile River Annual Flow (1871-1970). Each technique&apos;s sample was chosen to be a canonical or otherwise appropriate input. This is the same data you can use with the technique&apos;s Quick Action button or by selecting it in the Technique Explorer.' />
                <button id='btnSample_local_level'
                        label='Local Level Data: Nile River Annual Flow (1871-1970)'
                        imageMso='TableInsertExcel'
                        onAction='OnSampleDataByTechnique'
                        tag='local_level'
                        screentip='Sample data for Local Level Model'
                        supertip='Load a representative sample dataset for the Local Level Model technique. Dataset: Nile River Annual Flow (1871-1970). Each technique&apos;s sample was chosen to be a canonical or otherwise appropriate input. This is the same data you can use with the technique&apos;s Quick Action button or by selecting it in the Technique Explorer.' />
                <button id='btnSample_local_linear_trend'
                        label='Local Linear Trend Data: Airline Passengers (Monthly 1949-60)'
                        imageMso='TableInsertExcel'
                        onAction='OnSampleDataByTechnique'
                        tag='local_linear_trend'
                        screentip='Sample data for Local Linear Trend'
                        supertip='Load a representative sample dataset for the Local Linear Trend technique. Dataset: Airline Passengers (Monthly 1949-60). Each technique&apos;s sample was chosen to be a canonical or otherwise appropriate input. This is the same data you can use with the technique&apos;s Quick Action button or by selecting it in the Technique Explorer.' />
                <button id='btnSample_structural_ts'
                        label='Structural TS Data: Airline Passengers (Monthly 1949-60)'
                        imageMso='TableInsertExcel'
                        onAction='OnSampleDataByTechnique'
                        tag='structural_ts'
                        screentip='Sample data for Structural Time Series (UCM)'
                        supertip='Load a representative sample dataset for the Structural Time Series (UCM) technique. Dataset: Airline Passengers (Monthly 1949-60). Each technique&apos;s sample was chosen to be a canonical or otherwise appropriate input. This is the same data you can use with the technique&apos;s Quick Action button or by selecting it in the Technique Explorer.' />
                <button id='btnSample_particle_filter'
                        label='Particle Filter Data: Nile River Annual Flow (1871-1970)'
                        imageMso='TableInsertExcel'
                        onAction='OnSampleDataByTechnique'
                        tag='particle_filter'
                        screentip='Sample data for Particle Filter'
                        supertip='Load a representative sample dataset for the Particle Filter technique. Dataset: Nile River Annual Flow (1871-1970). Each technique&apos;s sample was chosen to be a canonical or otherwise appropriate input. This is the same data you can use with the technique&apos;s Quick Action button or by selecting it in the Technique Explorer.' />
              </menu>
              <menu id='menuSample_regime' label='Regimes / Nonlinear'>
                <button id='btnSample_markov_switching'
                        label='Markov Switching Data: US Real GDP Growth (Quarterly SAAR)'
                        imageMso='TableInsertExcel'
                        onAction='OnSampleDataByTechnique'
                        tag='markov_switching'
                        screentip='Sample data for Markov Switching Model'
                        supertip='Load a representative sample dataset for the Markov Switching Model technique. Dataset: US Real GDP Growth (Quarterly SAAR). Each technique&apos;s sample was chosen to be a canonical or otherwise appropriate input. This is the same data you can use with the technique&apos;s Quick Action button or by selecting it in the Technique Explorer.' />
                <button id='btnSample_hmm'
                        label='HMM Data: US Real GDP Growth (Quarterly SAAR)'
                        imageMso='TableInsertExcel'
                        onAction='OnSampleDataByTechnique'
                        tag='hmm'
                        screentip='Sample data for Hidden Markov Model'
                        supertip='Load a representative sample dataset for the Hidden Markov Model technique. Dataset: US Real GDP Growth (Quarterly SAAR). Each technique&apos;s sample was chosen to be a canonical or otherwise appropriate input. This is the same data you can use with the technique&apos;s Quick Action button or by selecting it in the Technique Explorer.' />
                <button id='btnSample_tar_setar'
                        label='TAR / SETAR Data: US Real GDP Growth (Quarterly SAAR)'
                        imageMso='TableInsertExcel'
                        onAction='OnSampleDataByTechnique'
                        tag='tar_setar'
                        screentip='Sample data for TAR / SETAR'
                        supertip='Load a representative sample dataset for the TAR / SETAR technique. Dataset: US Real GDP Growth (Quarterly SAAR). Each technique&apos;s sample was chosen to be a canonical or otherwise appropriate input. This is the same data you can use with the technique&apos;s Quick Action button or by selecting it in the Technique Explorer.' />
                <button id='btnSample_star'
                        label='STAR Data: S&amp;P 500 Daily Log Returns (2016-present)'
                        imageMso='TableInsertExcel'
                        onAction='OnSampleDataByTechnique'
                        tag='star'
                        screentip='Sample data for STAR Model'
                        supertip='Load a representative sample dataset for the STAR Model technique. Dataset: S&amp;P 500 Daily Log Returns (2016-present). Each technique&apos;s sample was chosen to be a canonical or otherwise appropriate input. This is the same data you can use with the technique&apos;s Quick Action button or by selecting it in the Technique Explorer.' />
                <button id='btnSample_nar_narx'
                        label='NAR / NARX Data: US Macro Quarterly (GDP, CPI, FF, UNRATE)'
                        imageMso='TableInsertExcel'
                        onAction='OnSampleDataByTechnique'
                        tag='nar_narx'
                        screentip='Sample data for NAR / NARX'
                        supertip='Load a representative sample dataset for the NAR / NARX technique. Dataset: US Macro Quarterly (GDP, CPI, FF, UNRATE). Each technique&apos;s sample was chosen to be a canonical or otherwise appropriate input. This is the same data you can use with the technique&apos;s Quick Action button or by selecting it in the Technique Explorer.' />
              </menu>
              <menu id='menuSample_vol' label='Volatility / Risk / Tails'>
                <button id='btnSample_garch'
                        label='GARCH Data: S&amp;P 500 Daily Log Returns (2016-present)'
                        imageMso='TableInsertExcel'
                        onAction='OnSampleDataByTechnique'
                        tag='garch'
                        screentip='Sample data for GARCH'
                        supertip='Load a representative sample dataset for the GARCH technique. Dataset: S&amp;P 500 Daily Log Returns (2016-present). Each technique&apos;s sample was chosen to be a canonical or otherwise appropriate input. This is the same data you can use with the technique&apos;s Quick Action button or by selecting it in the Technique Explorer.' />
                <button id='btnSample_gjr_garch'
                        label='GJR-GARCH Data: S&amp;P 500 Daily Log Returns (2016-present)'
                        imageMso='TableInsertExcel'
                        onAction='OnSampleDataByTechnique'
                        tag='gjr_garch'
                        screentip='Sample data for GJR-GARCH'
                        supertip='Load a representative sample dataset for the GJR-GARCH technique. Dataset: S&amp;P 500 Daily Log Returns (2016-present). Each technique&apos;s sample was chosen to be a canonical or otherwise appropriate input. This is the same data you can use with the technique&apos;s Quick Action button or by selecting it in the Technique Explorer.' />
                <button id='btnSample_egarch'
                        label='EGARCH Data: S&amp;P 500 Daily Log Returns (2016-present)'
                        imageMso='TableInsertExcel'
                        onAction='OnSampleDataByTechnique'
                        tag='egarch'
                        screentip='Sample data for EGARCH'
                        supertip='Load a representative sample dataset for the EGARCH technique. Dataset: S&amp;P 500 Daily Log Returns (2016-present). Each technique&apos;s sample was chosen to be a canonical or otherwise appropriate input. This is the same data you can use with the technique&apos;s Quick Action button or by selecting it in the Technique Explorer.' />
                <button id='btnSample_stochastic_volatility'
                        label='Stochastic Vol Data: S&amp;P 500 Daily Log Returns (2016-present)'
                        imageMso='TableInsertExcel'
                        onAction='OnSampleDataByTechnique'
                        tag='stochastic_volatility'
                        screentip='Sample data for Stochastic Volatility'
                        supertip='Load a representative sample dataset for the Stochastic Volatility technique. Dataset: S&amp;P 500 Daily Log Returns (2016-present). Each technique&apos;s sample was chosen to be a canonical or otherwise appropriate input. This is the same data you can use with the technique&apos;s Quick Action button or by selecting it in the Technique Explorer.' />
                <button id='btnSample_har_rv'
                        label='HAR-RV Data: S&amp;P 500 Daily Log Returns (2016-present)'
                        imageMso='TableInsertExcel'
                        onAction='OnSampleDataByTechnique'
                        tag='har_rv'
                        screentip='Sample data for HAR-RV'
                        supertip='Load a representative sample dataset for the HAR-RV technique. Dataset: S&amp;P 500 Daily Log Returns (2016-present). Each technique&apos;s sample was chosen to be a canonical or otherwise appropriate input. This is the same data you can use with the technique&apos;s Quick Action button or by selecting it in the Technique Explorer.' />
                <button id='btnSample_evt_pot_gpd'
                        label='EVT (POT/GPD) Data: S&amp;P 500 Daily Log Returns (2016-present)'
                        imageMso='TableInsertExcel'
                        onAction='OnSampleDataByTechnique'
                        tag='evt_pot_gpd'
                        screentip='Sample data for EVT: POT / GPD'
                        supertip='Load a representative sample dataset for the EVT: POT / GPD technique. Dataset: S&amp;P 500 Daily Log Returns (2016-present). Each technique&apos;s sample was chosen to be a canonical or otherwise appropriate input. This is the same data you can use with the technique&apos;s Quick Action button or by selecting it in the Technique Explorer.' />
                <button id='btnSample_caviar_quantile_dynamics'
                        label='CAViaR Data: S&amp;P 500 Daily Log Returns (2016-present)'
                        imageMso='TableInsertExcel'
                        onAction='OnSampleDataByTechnique'
                        tag='caviar_quantile_dynamics'
                        screentip='Sample data for CAViaR Quantile Dynamics'
                        supertip='Load a representative sample dataset for the CAViaR Quantile Dynamics technique. Dataset: S&amp;P 500 Daily Log Returns (2016-present). Each technique&apos;s sample was chosen to be a canonical or otherwise appropriate input. This is the same data you can use with the technique&apos;s Quick Action button or by selecting it in the Technique Explorer.' />
              </menu>
              <menu id='menuSample_freq' label='Frequency Domain / Signal'>
                <button id='btnSample_fft_spectrum'
                        label='FFT Data: Monthly Sunspots (1749-present)'
                        imageMso='TableInsertExcel'
                        onAction='OnSampleDataByTechnique'
                        tag='fft_spectrum'
                        screentip='Sample data for FFT Spectrum'
                        supertip='Load a representative sample dataset for the FFT Spectrum technique. Dataset: Monthly Sunspots (1749-present). Each technique&apos;s sample was chosen to be a canonical or otherwise appropriate input. This is the same data you can use with the technique&apos;s Quick Action button or by selecting it in the Technique Explorer.' />
                <button id='btnSample_periodogram_spectral_density'
                        label='Periodogram Data: Monthly Sunspots (1749-present)'
                        imageMso='TableInsertExcel'
                        onAction='OnSampleDataByTechnique'
                        tag='periodogram_spectral_density'
                        screentip='Sample data for Periodogram Spectral Density'
                        supertip='Load a representative sample dataset for the Periodogram Spectral Density technique. Dataset: Monthly Sunspots (1749-present). Each technique&apos;s sample was chosen to be a canonical or otherwise appropriate input. This is the same data you can use with the technique&apos;s Quick Action button or by selecting it in the Technique Explorer.' />
                <button id='btnSample_lomb_scargle'
                        label='Lomb-Scargle Data: Monthly Sunspots (1749-present)'
                        imageMso='TableInsertExcel'
                        onAction='OnSampleDataByTechnique'
                        tag='lomb_scargle'
                        screentip='Sample data for Lomb-Scargle Periodogram'
                        supertip='Load a representative sample dataset for the Lomb-Scargle Periodogram technique. Dataset: Monthly Sunspots (1749-present). Each technique&apos;s sample was chosen to be a canonical or otherwise appropriate input. This is the same data you can use with the technique&apos;s Quick Action button or by selecting it in the Technique Explorer.' />
                <button id='btnSample_wavelet_transform'
                        label='Wavelet Data: Monthly Sunspots (1749-present)'
                        imageMso='TableInsertExcel'
                        onAction='OnSampleDataByTechnique'
                        tag='wavelet_transform'
                        screentip='Sample data for Wavelet Transform'
                        supertip='Load a representative sample dataset for the Wavelet Transform technique. Dataset: Monthly Sunspots (1749-present). Each technique&apos;s sample was chosen to be a canonical or otherwise appropriate input. This is the same data you can use with the technique&apos;s Quick Action button or by selecting it in the Technique Explorer.' />
                <button id='btnSample_wavelet_coherence_phase_lag'
                        label='Wavelet Coherence Data: US Macro Quarterly (GDP, CPI, FF, UNRATE)'
                        imageMso='TableInsertExcel'
                        onAction='OnSampleDataByTechnique'
                        tag='wavelet_coherence_phase_lag'
                        screentip='Sample data for Wavelet Coherence &amp; Phase-Lag'
                        supertip='Load a representative sample dataset for the Wavelet Coherence &amp; Phase-Lag technique. Dataset: US Macro Quarterly (GDP, CPI, FF, UNRATE). Each technique&apos;s sample was chosen to be a canonical or otherwise appropriate input. This is the same data you can use with the technique&apos;s Quick Action button or by selecting it in the Technique Explorer.' />
                <button id='btnSample_ssa'
                        label='SSA Data: Monthly Sunspots (1749-present)'
                        imageMso='TableInsertExcel'
                        onAction='OnSampleDataByTechnique'
                        tag='ssa'
                        screentip='Sample data for Singular Spectrum Analysis'
                        supertip='Load a representative sample dataset for the Singular Spectrum Analysis technique. Dataset: Monthly Sunspots (1749-present). Each technique&apos;s sample was chosen to be a canonical or otherwise appropriate input. This is the same data you can use with the technique&apos;s Quick Action button or by selecting it in the Technique Explorer.' />
                <button id='btnSample_emd_hht'
                        label='EMD / Hilbert-Huang Data: Monthly Sunspots (1749-present)'
                        imageMso='TableInsertExcel'
                        onAction='OnSampleDataByTechnique'
                        tag='emd_hht'
                        screentip='Sample data for EMD / Hilbert-Huang Transform'
                        supertip='Load a representative sample dataset for the EMD / Hilbert-Huang Transform technique. Dataset: Monthly Sunspots (1749-present). Each technique&apos;s sample was chosen to be a canonical or otherwise appropriate input. This is the same data you can use with the technique&apos;s Quick Action button or by selecting it in the Technique Explorer.' />
              </menu>
              <menu id='menuSample_cp' label='Change Points / Anomalies / Interventions'>
                <button id='btnSample_pelt_change_points'
                        label='PELT Data: Nile River Annual Flow (1871-1970)'
                        imageMso='TableInsertExcel'
                        onAction='OnSampleDataByTechnique'
                        tag='pelt_change_points'
                        screentip='Sample data for PELT Change Points'
                        supertip='Load a representative sample dataset for the PELT Change Points technique. Dataset: Nile River Annual Flow (1871-1970). Each technique&apos;s sample was chosen to be a canonical or otherwise appropriate input. This is the same data you can use with the technique&apos;s Quick Action button or by selecting it in the Technique Explorer.' />
                <button id='btnSample_bocpd'
                        label='BOCPD Data: Nile River Annual Flow (1871-1970)'
                        imageMso='TableInsertExcel'
                        onAction='OnSampleDataByTechnique'
                        tag='bocpd'
                        screentip='Sample data for Bayesian Online Change Point Detection'
                        supertip='Load a representative sample dataset for the Bayesian Online Change Point Detection technique. Dataset: Nile River Annual Flow (1871-1970). Each technique&apos;s sample was chosen to be a canonical or otherwise appropriate input. This is the same data you can use with the technique&apos;s Quick Action button or by selecting it in the Technique Explorer.' />
                <button id='btnSample_cusum_page_hinkley'
                        label='CUSUM Data: Nile River Annual Flow (1871-1970)'
                        imageMso='TableInsertExcel'
                        onAction='OnSampleDataByTechnique'
                        tag='cusum_page_hinkley'
                        screentip='Sample data for CUSUM / Page-Hinkley'
                        supertip='Load a representative sample dataset for the CUSUM / Page-Hinkley technique. Dataset: Nile River Annual Flow (1871-1970). Each technique&apos;s sample was chosen to be a canonical or otherwise appropriate input. This is the same data you can use with the technique&apos;s Quick Action button or by selecting it in the Technique Explorer.' />
                <button id='btnSample_stl_esd_anomaly'
                        label='STL+ESD Anomaly Data: Airline Passengers (Monthly 1949-60)'
                        imageMso='TableInsertExcel'
                        onAction='OnSampleDataByTechnique'
                        tag='stl_esd_anomaly'
                        screentip='Sample data for STL + ESD Anomaly Detection'
                        supertip='Load a representative sample dataset for the STL + ESD Anomaly Detection technique. Dataset: Airline Passengers (Monthly 1949-60). Each technique&apos;s sample was chosen to be a canonical or otherwise appropriate input. This is the same data you can use with the technique&apos;s Quick Action button or by selecting it in the Technique Explorer.' />
                <button id='btnSample_intervention_analysis'
                        label='Intervention Data: Nile River Annual Flow (1871-1970)'
                        imageMso='TableInsertExcel'
                        onAction='OnSampleDataByTechnique'
                        tag='intervention_analysis'
                        screentip='Sample data for Intervention Analysis'
                        supertip='Load a representative sample dataset for the Intervention Analysis technique. Dataset: Nile River Annual Flow (1871-1970). Each technique&apos;s sample was chosen to be a canonical or otherwise appropriate input. This is the same data you can use with the technique&apos;s Quick Action button or by selecting it in the Technique Explorer.' />
              </menu>
              <menu id='menuSample_cause' label='Causality / Relationships / Lead-Lag'>
                <button id='btnSample_granger_causality'
                        label='Granger Data: US Macro Quarterly (GDP, CPI, FF, UNRATE)'
                        imageMso='TableInsertExcel'
                        onAction='OnSampleDataByTechnique'
                        tag='granger_causality'
                        screentip='Sample data for Granger Causality Test'
                        supertip='Load a representative sample dataset for the Granger Causality Test technique. Dataset: US Macro Quarterly (GDP, CPI, FF, UNRATE). Each technique&apos;s sample was chosen to be a canonical or otherwise appropriate input. This is the same data you can use with the technique&apos;s Quick Action button or by selecting it in the Technique Explorer.' />
                <button id='btnSample_cross_correlation_lag'
                        label='CCF Lag Data: US Macro Quarterly (GDP, CPI, FF, UNRATE)'
                        imageMso='TableInsertExcel'
                        onAction='OnSampleDataByTechnique'
                        tag='cross_correlation_lag'
                        screentip='Sample data for Cross-Correlation Lag'
                        supertip='Load a representative sample dataset for the Cross-Correlation Lag technique. Dataset: US Macro Quarterly (GDP, CPI, FF, UNRATE). Each technique&apos;s sample was chosen to be a canonical or otherwise appropriate input. This is the same data you can use with the technique&apos;s Quick Action button or by selecting it in the Technique Explorer.' />
                <button id='btnSample_prewhitened_ccf_lag'
                        label='Prewhitened CCF Data: US Macro Quarterly (GDP, CPI, FF, UNRATE)'
                        imageMso='TableInsertExcel'
                        onAction='OnSampleDataByTechnique'
                        tag='prewhitened_ccf_lag'
                        screentip='Sample data for Prewhitened CCF Lag'
                        supertip='Load a representative sample dataset for the Prewhitened CCF Lag technique. Dataset: US Macro Quarterly (GDP, CPI, FF, UNRATE). Each technique&apos;s sample was chosen to be a canonical or otherwise appropriate input. This is the same data you can use with the technique&apos;s Quick Action button or by selecting it in the Technique Explorer.' />
                <button id='btnSample_gcc_phat_delay'
                        label='GCC-PHAT Data: US Macro Quarterly (GDP, CPI, FF, UNRATE)'
                        imageMso='TableInsertExcel'
                        onAction='OnSampleDataByTechnique'
                        tag='gcc_phat_delay'
                        screentip='Sample data for GCC-PHAT Delay Estimation'
                        supertip='Load a representative sample dataset for the GCC-PHAT Delay Estimation technique. Dataset: US Macro Quarterly (GDP, CPI, FF, UNRATE). Each technique&apos;s sample was chosen to be a canonical or otherwise appropriate input. This is the same data you can use with the technique&apos;s Quick Action button or by selecting it in the Technique Explorer.' />
                <button id='btnSample_rolling_ccf_lag'
                        label='Rolling CCF Data: US Macro Quarterly (GDP, CPI, FF, UNRATE)'
                        imageMso='TableInsertExcel'
                        onAction='OnSampleDataByTechnique'
                        tag='rolling_ccf_lag'
                        screentip='Sample data for Rolling CCF Lag (Time-Varying)'
                        supertip='Load a representative sample dataset for the Rolling CCF Lag (Time-Varying) technique. Dataset: US Macro Quarterly (GDP, CPI, FF, UNRATE). Each technique&apos;s sample was chosen to be a canonical or otherwise appropriate input. This is the same data you can use with the technique&apos;s Quick Action button or by selecting it in the Technique Explorer.' />
                <button id='btnSample_dtw_alignment_lag'
                        label='DTW Data: US Macro Quarterly (GDP, CPI, FF, UNRATE)'
                        imageMso='TableInsertExcel'
                        onAction='OnSampleDataByTechnique'
                        tag='dtw_alignment_lag'
                        screentip='Sample data for DTW Alignment Lag (Time-Varying)'
                        supertip='Load a representative sample dataset for the DTW Alignment Lag (Time-Varying) technique. Dataset: US Macro Quarterly (GDP, CPI, FF, UNRATE). Each technique&apos;s sample was chosen to be a canonical or otherwise appropriate input. This is the same data you can use with the technique&apos;s Quick Action button or by selecting it in the Technique Explorer.' />
              </menu>
              <menu id='menuSample_eval' label='Evaluation / Uncertainty'>
                <button id='btnSample_rolling_origin_cv'
                        label='Rolling CV Data: US Real GDP Growth (Quarterly SAAR)'
                        imageMso='TableInsertExcel'
                        onAction='OnSampleDataByTechnique'
                        tag='rolling_origin_cv'
                        screentip='Sample data for Rolling Origin Cross-Validation'
                        supertip='Load a representative sample dataset for the Rolling Origin Cross-Validation technique. Dataset: US Real GDP Growth (Quarterly SAAR). Each technique&apos;s sample was chosen to be a canonical or otherwise appropriate input. This is the same data you can use with the technique&apos;s Quick Action button or by selecting it in the Technique Explorer.' />
                <button id='btnSample_block_bootstrap'
                        label='Block Bootstrap Data: S&amp;P 500 Daily Log Returns (2016-present)'
                        imageMso='TableInsertExcel'
                        onAction='OnSampleDataByTechnique'
                        tag='block_bootstrap'
                        screentip='Sample data for Block Bootstrap'
                        supertip='Load a representative sample dataset for the Block Bootstrap technique. Dataset: S&amp;P 500 Daily Log Returns (2016-present). Each technique&apos;s sample was chosen to be a canonical or otherwise appropriate input. This is the same data you can use with the technique&apos;s Quick Action button or by selecting it in the Technique Explorer.' />
                <button id='btnSample_conformal_intervals'
                        label='Conformal Data: US Real GDP Growth (Quarterly SAAR)'
                        imageMso='TableInsertExcel'
                        onAction='OnSampleDataByTechnique'
                        tag='conformal_intervals'
                        screentip='Sample data for Conformal Prediction Intervals'
                        supertip='Load a representative sample dataset for the Conformal Prediction Intervals technique. Dataset: US Real GDP Growth (Quarterly SAAR). Each technique&apos;s sample was chosen to be a canonical or otherwise appropriate input. This is the same data you can use with the technique&apos;s Quick Action button or by selecting it in the Technique Explorer.' />
                <button id='btnSample_forecast_combination'
                        label='Forecast Combination Data: US Real GDP Growth (Quarterly SAAR)'
                        imageMso='TableInsertExcel'
                        onAction='OnSampleDataByTechnique'
                        tag='forecast_combination'
                        screentip='Sample data for Forecast Combination'
                        supertip='Load a representative sample dataset for the Forecast Combination technique. Dataset: US Real GDP Growth (Quarterly SAAR). Each technique&apos;s sample was chosen to be a canonical or otherwise appropriate input. This is the same data you can use with the technique&apos;s Quick Action button or by selecting it in the Technique Explorer.' />
                <button id='btnSample_robust_estimators'
                        label='Robust Estimators Data: S&amp;P 500 Daily Log Returns (2016-present)'
                        imageMso='TableInsertExcel'
                        onAction='OnSampleDataByTechnique'
                        tag='robust_estimators'
                        screentip='Sample data for Robust Estimators'
                        supertip='Load a representative sample dataset for the Robust Estimators technique. Dataset: S&amp;P 500 Daily Log Returns (2016-present). Each technique&apos;s sample was chosen to be a canonical or otherwise appropriate input. This is the same data you can use with the technique&apos;s Quick Action button or by selecting it in the Technique Explorer.' />
              </menu>
              <menu id='menuSample_miss' label='Missing Data / Temporal Disaggregation'>
                <button id='btnSample_kalman_imputation'
                        label='Kalman Imputation Data: Airline Passengers (Monthly 1949-60)'
                        imageMso='TableInsertExcel'
                        onAction='OnSampleDataByTechnique'
                        tag='kalman_imputation'
                        screentip='Sample data for Kalman Imputation'
                        supertip='Load a representative sample dataset for the Kalman Imputation technique. Dataset: Airline Passengers (Monthly 1949-60). Each technique&apos;s sample was chosen to be a canonical or otherwise appropriate input. This is the same data you can use with the technique&apos;s Quick Action button or by selecting it in the Technique Explorer.' />
                <button id='btnSample_loess_interpolation'
                        label='LOESS Data: Airline Passengers (Monthly 1949-60)'
                        imageMso='TableInsertExcel'
                        onAction='OnSampleDataByTechnique'
                        tag='loess_interpolation'
                        screentip='Sample data for LOESS Interpolation'
                        supertip='Load a representative sample dataset for the LOESS Interpolation technique. Dataset: Airline Passengers (Monthly 1949-60). Each technique&apos;s sample was chosen to be a canonical or otherwise appropriate input. This is the same data you can use with the technique&apos;s Quick Action button or by selecting it in the Technique Explorer.' />
                <button id='btnSample_denton_chowlin_disaggregation'
                        label='Denton/Chow-Lin Data: Quarterly GDP + Monthly IP for Disaggregation'
                        imageMso='TableInsertExcel'
                        onAction='OnSampleDataByTechnique'
                        tag='denton_chowlin_disaggregation'
                        screentip='Sample data for Denton / Chow-Lin Disaggregation'
                        supertip='Load a representative sample dataset for the Denton / Chow-Lin Disaggregation technique. Dataset: Quarterly GDP + Monthly IP for Disaggregation. Each technique&apos;s sample was chosen to be a canonical or otherwise appropriate input. This is the same data you can use with the technique&apos;s Quick Action button or by selecting it in the Technique Explorer.' />
              </menu>
              <menu id='menuSample_ml' label='ML / Deep Learning'>
                <button id='btnSample_gradient_boosting_forecast'
                        label='Gradient Boosting Data: US Macro Quarterly (GDP, CPI, FF, UNRATE)'
                        imageMso='TableInsertExcel'
                        onAction='OnSampleDataByTechnique'
                        tag='gradient_boosting_forecast'
                        screentip='Sample data for Gradient Boosting Forecast'
                        supertip='Load a representative sample dataset for the Gradient Boosting Forecast technique. Dataset: US Macro Quarterly (GDP, CPI, FF, UNRATE). Each technique&apos;s sample was chosen to be a canonical or otherwise appropriate input. This is the same data you can use with the technique&apos;s Quick Action button or by selecting it in the Technique Explorer.' />
                <button id='btnSample_quantile_regression'
                        label='Quantile Regression Data: US Real GDP Growth (Quarterly SAAR)'
                        imageMso='TableInsertExcel'
                        onAction='OnSampleDataByTechnique'
                        tag='quantile_regression'
                        screentip='Sample data for Quantile Regression Forecast'
                        supertip='Load a representative sample dataset for the Quantile Regression Forecast technique. Dataset: US Real GDP Growth (Quarterly SAAR). Each technique&apos;s sample was chosen to be a canonical or otherwise appropriate input. This is the same data you can use with the technique&apos;s Quick Action button or by selecting it in the Technique Explorer.' />
                <button id='btnSample_gaussian_process_forecast'
                        label='Gaussian Process Data: US Real GDP Growth (Quarterly SAAR)'
                        imageMso='TableInsertExcel'
                        onAction='OnSampleDataByTechnique'
                        tag='gaussian_process_forecast'
                        screentip='Sample data for Gaussian Process Forecast'
                        supertip='Load a representative sample dataset for the Gaussian Process Forecast technique. Dataset: US Real GDP Growth (Quarterly SAAR). Each technique&apos;s sample was chosen to be a canonical or otherwise appropriate input. This is the same data you can use with the technique&apos;s Quick Action button or by selecting it in the Technique Explorer.' />
                <button id='btnSample_lstm_gru_forecast'
                        label='LSTM/GRU Data: Airline Passengers (Monthly 1949-60)'
                        imageMso='TableInsertExcel'
                        onAction='OnSampleDataByTechnique'
                        tag='lstm_gru_forecast'
                        screentip='Sample data for LSTM / GRU Forecast'
                        supertip='Load a representative sample dataset for the LSTM / GRU Forecast technique. Dataset: Airline Passengers (Monthly 1949-60). Each technique&apos;s sample was chosen to be a canonical or otherwise appropriate input. This is the same data you can use with the technique&apos;s Quick Action button or by selecting it in the Technique Explorer.' />
                <button id='btnSample_tcn_forecast'
                        label='TCN Data: Airline Passengers (Monthly 1949-60)'
                        imageMso='TableInsertExcel'
                        onAction='OnSampleDataByTechnique'
                        tag='tcn_forecast'
                        screentip='Sample data for TCN Forecast'
                        supertip='Load a representative sample dataset for the TCN Forecast technique. Dataset: Airline Passengers (Monthly 1949-60). Each technique&apos;s sample was chosen to be a canonical or otherwise appropriate input. This is the same data you can use with the technique&apos;s Quick Action button or by selecting it in the Technique Explorer.' />
                <button id='btnSample_nbeats_forecast'
                        label='N-BEATS Data: Airline Passengers (Monthly 1949-60)'
                        imageMso='TableInsertExcel'
                        onAction='OnSampleDataByTechnique'
                        tag='nbeats_forecast'
                        screentip='Sample data for N-BEATS Forecast'
                        supertip='Load a representative sample dataset for the N-BEATS Forecast technique. Dataset: Airline Passengers (Monthly 1949-60). Each technique&apos;s sample was chosen to be a canonical or otherwise appropriate input. This is the same data you can use with the technique&apos;s Quick Action button or by selecting it in the Technique Explorer.' />
                <button id='btnSample_transformer_forecast'
                        label='Transformer Data: Airline Passengers (Monthly 1949-60)'
                        imageMso='TableInsertExcel'
                        onAction='OnSampleDataByTechnique'
                        tag='transformer_forecast'
                        screentip='Sample data for Transformer Forecast'
                        supertip='Load a representative sample dataset for the Transformer Forecast technique. Dataset: Airline Passengers (Monthly 1949-60). Each technique&apos;s sample was chosen to be a canonical or otherwise appropriate input. This is the same data you can use with the technique&apos;s Quick Action button or by selecting it in the Technique Explorer.' />
                <button id='btnSample_prophet_forecast'
                        label='Prophet Data: Airline Passengers (Monthly 1949-60)'
                        imageMso='TableInsertExcel'
                        onAction='OnSampleDataByTechnique'
                        tag='prophet_forecast'
                        screentip='Sample data for Prophet Forecast'
                        supertip='Load a representative sample dataset for the Prophet Forecast technique. Dataset: Airline Passengers (Monthly 1949-60). Each technique&apos;s sample was chosen to be a canonical or otherwise appropriate input. This is the same data you can use with the technique&apos;s Quick Action button or by selecting it in the Technique Explorer.' />
                <button id='btnSample_random_forest_forecast'
                        label='Random Forest Data: US Macro Quarterly (GDP, CPI, FF, UNRATE)'
                        imageMso='TableInsertExcel'
                        onAction='OnSampleDataByTechnique'
                        tag='random_forest_forecast'
                        screentip='Sample data for Random Forest Forecast'
                        supertip='Load a representative sample dataset for the Random Forest Forecast technique. Dataset: US Macro Quarterly (GDP, CPI, FF, UNRATE). Each technique&apos;s sample was chosen to be a canonical or otherwise appropriate input. This is the same data you can use with the technique&apos;s Quick Action button or by selecting it in the Technique Explorer.' />
                <button id='btnSample_xgboost_forecast'
                        label='XGBoost Data: US Macro Quarterly (GDP, CPI, FF, UNRATE)'
                        imageMso='TableInsertExcel'
                        onAction='OnSampleDataByTechnique'
                        tag='xgboost_forecast'
                        screentip='Sample data for XGBoost Forecast'
                        supertip='Load a representative sample dataset for the XGBoost Forecast technique. Dataset: US Macro Quarterly (GDP, CPI, FF, UNRATE). Each technique&apos;s sample was chosen to be a canonical or otherwise appropriate input. This is the same data you can use with the technique&apos;s Quick Action button or by selecting it in the Technique Explorer.' />
                <button id='btnSample_svr_forecast'
                        label='SVR Data: US Real GDP Growth (Quarterly SAAR)'
                        imageMso='TableInsertExcel'
                        onAction='OnSampleDataByTechnique'
                        tag='svr_forecast'
                        screentip='Sample data for SVR Forecast'
                        supertip='Load a representative sample dataset for the SVR Forecast technique. Dataset: US Real GDP Growth (Quarterly SAAR). Each technique&apos;s sample was chosen to be a canonical or otherwise appropriate input. This is the same data you can use with the technique&apos;s Quick Action button or by selecting it in the Technique Explorer.' />
                <button id='btnSample_autoencoder_anomaly'
                        label='Autoencoder Data: S&amp;P 500 Daily Log Returns (2016-present)'
                        imageMso='TableInsertExcel'
                        onAction='OnSampleDataByTechnique'
                        tag='autoencoder_anomaly'
                        screentip='Sample data for Autoencoder Anomaly Detection'
                        supertip='Load a representative sample dataset for the Autoencoder Anomaly Detection technique. Dataset: S&amp;P 500 Daily Log Returns (2016-present). Each technique&apos;s sample was chosen to be a canonical or otherwise appropriate input. This is the same data you can use with the technique&apos;s Quick Action button or by selecting it in the Technique Explorer.' />
                <button id='btnSample_nhits_forecast'
                        label='N-HiTS Data: Airline Passengers (Monthly 1949-60)'
                        imageMso='TableInsertExcel'
                        onAction='OnSampleDataByTechnique'
                        tag='nhits_forecast'
                        screentip='Sample data for N-HiTS Forecast'
                        supertip='Load a representative sample dataset for the N-HiTS Forecast technique. Dataset: Airline Passengers (Monthly 1949-60). Each technique&apos;s sample was chosen to be a canonical or otherwise appropriate input. This is the same data you can use with the technique&apos;s Quick Action button or by selecting it in the Technique Explorer.' />
                <button id='btnSample_echo_state_network'
                        label='ESN Data: Monthly Sunspots (1749-present)'
                        imageMso='TableInsertExcel'
                        onAction='OnSampleDataByTechnique'
                        tag='echo_state_network'
                        screentip='Sample data for Echo State Network'
                        supertip='Load a representative sample dataset for the Echo State Network technique. Dataset: Monthly Sunspots (1749-present). Each technique&apos;s sample was chosen to be a canonical or otherwise appropriate input. This is the same data you can use with the technique&apos;s Quick Action button or by selecting it in the Technique Explorer.' />
                <button id='btnSample_lightgbm_forecast'
                        label='LightGBM Data: US Macro Quarterly (GDP, CPI, FF, UNRATE)'
                        imageMso='TableInsertExcel'
                        onAction='OnSampleDataByTechnique'
                        tag='lightgbm_forecast'
                        screentip='Sample data for LightGBM Forecast'
                        supertip='Load a representative sample dataset for the LightGBM Forecast technique. Dataset: US Macro Quarterly (GDP, CPI, FF, UNRATE). Each technique&apos;s sample was chosen to be a canonical or otherwise appropriate input. This is the same data you can use with the technique&apos;s Quick Action button or by selecting it in the Technique Explorer.' />
              </menu>
            </menu>
          </splitButton>
          <button id='btnSaveInstaller'
                  label='Save Installer'
                  size='large'
                  imageMso='FileSaveAs'
                  onAction='OnSaveInstaller'
                  screentip='Save Installer Package'
                  supertip='Save a copy of the Time Series Lab installer to a location of your choice, so you can distribute it to another PC.' />
          <button id='btnAbout'
                  label='About'
                  size='large'
                  imageMso='Info'
                  onAction='OnAbout'
                  screentip='About Time Series Lab'
                  supertip='Version information and diagnostics.' />
        </group>

      </tab>
    </tabs>
  </ribbon>
</customUI>";
        }
    }
}
