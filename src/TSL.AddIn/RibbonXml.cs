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

        <group id='grpQuickActions' label='Quick Actions'>
          <button id='btnSeasonalAdj'
                  label='Seasonal Adjustment'
                  size='large'
                  imageMso='ChartAreaChart'
                  onAction='OnSeasonalAdjustment'
                  screentip='Seasonal Adjustment'
                  supertip='Decompose a time series into trend, seasonal, and remainder components using STL or other methods.' />
          <button id='btnGranger'
                  label='Granger Causality'
                  size='large'
                  imageMso='ChartRadarChart'
                  onAction='OnGrangerCausality'
                  screentip='Granger Causality Test'
                  supertip='Test whether one time series helps predict another.' />
          <button id='btnLeadLag'
                  label='Lead-Lag Finder'
                  size='large'
                  imageMso='ChartTypeLineInsertGallery'
                  onAction='OnLeadLagFinder'
                  screentip='Lead-Lag Analysis'
                  supertip='Find the time delay between two series using cross-correlation methods.' />
          <separator id='sepQA1' />
          <button id='btnForecast'
                  label='Forecast'
                  size='large'
                  imageMso='ChartTypeAreaInsertGallery'
                  onAction='OnForecast'
                  screentip='Forecast'
                  supertip='Generate forecasts with prediction intervals using automatic model selection.' />
          <button id='btnAnomaly'
                  label='Anomaly Scan'
                  size='large'
                  imageMso='TracePrecedents'
                  onAction='OnAnomalyScan'
                  screentip='Anomaly Detection'
                  supertip='Scan a time series for outliers and anomalous observations.' />
          <separator id='sepQA2' />
          <button id='btnPca'
                  label='PCA'
                  size='large'
                  imageMso='ChartTrendline'
                  onAction='OnPcaAnalysis'
                  screentip='Principal Component Analysis (PCA)'
                  supertip='Reduce a set of correlated time series into a smaller number of uncorrelated principal components, with loadings and explained variance.' />
          <button id='btnDfm'
                  label='DFM'
                  size='large'
                  imageMso='ChartLines'
                  onAction='OnDynamicFactorModel'
                  screentip='Dynamic Factor Model (DFM)'
                  supertip='Extract common latent factors that drive multiple time series jointly using a dynamic factor model.' />
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
          <dropDown id='ddPreset'
                    label='Preset'
                    sizeString='WWWWWWWWWWW'
                    getItemCount='OnPresetGetItemCount'
                    getItemLabel='OnPresetGetItemLabel'
                    getItemID='OnPresetGetItemId'
                    getSelectedItemIndex='OnPresetGetSelectedIndex'
                    onAction='OnPresetChange'
                    screentip='Analysis Preset'
                    supertip='Fast: quick results. Balanced: good defaults with cross-validation. Thorough: extensive search, manual recompute.' />
          <separator id='sepRun1' />
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
              <button id='btnSampleTreasury'
                      label='Treasury Yields (Daily)'
                      imageMso='TableInsertExcel'
                      onAction='OnSampleDataTreasury'
                      screentip='Treasury Yields'
                      supertip='Daily 2Y, 5Y, 10Y, and 30Y U.S. Treasury constant maturity yields from the Federal Reserve.' />
              <button id='btnSampleGdp'
                      label='Real GDP (Quarterly)'
                      imageMso='TableInsertExcel'
                      onAction='OnSampleDataGdp'
                      screentip='Real GDP'
                      supertip='U.S. real GDP growth Q/Q SAAR from the Bureau of Economic Analysis.' />
              <button id='btnSamplePce'
                      label='Core PCE (Quarterly)'
                      imageMso='TableInsertExcel'
                      onAction='OnSampleDataPce'
                      screentip='Core PCE Inflation'
                      supertip='Core PCE inflation Q/Q SAAR from the Bureau of Economic Analysis.' />
              <button id='btnSamplePayrollSa'
                      label='Nonfarm Payroll Job Gains, SA (Monthly)'
                      imageMso='TableInsertExcel'
                      onAction='OnSampleDataPayrollSa'
                      screentip='Nonfarm Payroll Job Gains (Seasonally Adjusted)'
                      supertip='Monthly change in U.S. total nonfarm payroll employment, seasonally adjusted (BLS series CES0000000001), in thousands of jobs. Goes back to February 1939.' />
              <button id='btnSamplePayrollNsa'
                      label='Nonfarm Payroll Job Gains, NSA (Monthly)'
                      imageMso='TableInsertExcel'
                      onAction='OnSampleDataPayrollNsa'
                      screentip='Nonfarm Payroll Job Gains (Not Seasonally Adjusted)'
                      supertip='Monthly change in U.S. total nonfarm payroll employment, not seasonally adjusted (BLS series CEU0000000001), in thousands of jobs. Goes back to February 1939.' />
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
