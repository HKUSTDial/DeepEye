// Helper function to get theme configuration (from template or use default)
function getThemeConfig() {
    // Get theme configuration from template (exposed via window.currentPalette and window.currentThemeName)
    if (window.currentPalette && window.currentThemeName) {
        return {
            palette: window.currentPalette,
            themeName: window.currentThemeName
        };
    }
    // Fallback to default theme (if template didn't load theme configuration)
    return {
        palette: null,
        themeName: null
    };
}

// Debounce utility function
function debounce(func, wait) {
    let timeout;
    return function(...args) {
        const context = this;
        clearTimeout(timeout);
        timeout = setTimeout(() => func.apply(context, args), wait);
    };
}

// Global switchPage function - must be defined before template loads
window.switchPage = function(pageId) {
    const overview = document.getElementById('page-overview');
    const details = document.getElementById('page-details');
    const navOverview = document.getElementById('nav-overview');
    const navDetails = document.getElementById('nav-details');
    const title = document.getElementById('page-title');

    if (!overview || !details || !navOverview || !navDetails || !title) {
        console.warn('Page elements not found, waiting for DOM...');
        setTimeout(() => window.switchPage(pageId), 100);
        return;
    }

    if (pageId === 'overview') {
        overview.classList.remove('hidden');
        details.classList.add('hidden');
        navOverview.classList.add('nav-active');
        navOverview.classList.remove('nav-inactive');
        navDetails.classList.add('nav-inactive');
        navDetails.classList.remove('nav-active');
        if (title) title.textContent = 'Dashboard Overview';
        setTimeout(() => {
            if (App.charts && Object.keys(App.charts).length > 0) {
                Object.values(App.charts).forEach(c => {
                    if (c && typeof c.resize === 'function') {
                        c.resize();
                    }
                });
            }
        }, 50);
    } else {
        overview.classList.add('hidden');
        details.classList.remove('hidden');
        navDetails.classList.add('nav-active');
        navDetails.classList.remove('nav-inactive');
        navOverview.classList.add('nav-inactive');
        navOverview.classList.remove('nav-active');
        if (title) title.textContent = 'Detailed Reports';
        // fetchRealData will be called if defined in template
        console.log('[switchPage] Switching to details page, checking fetchRealData...', typeof window.fetchRealData);
        
        // Try to call fetchRealData with retry mechanism
        const tryFetchData = (attempt = 0, maxAttempts = 10) => {
            if (typeof window.fetchRealData === 'function') {
                console.log('[switchPage] Calling fetchRealData...');
                window.fetchRealData();
            } else if (attempt < maxAttempts) {
                console.log(`[switchPage] fetchRealData not found, retrying... (${attempt + 1}/${maxAttempts})`);
                setTimeout(() => tryFetchData(attempt + 1, maxAttempts), 100);
            } else {
                console.error('[switchPage] fetchRealData still not found after all retries');
            }
        };
        
        tryFetchData();
    }
};

const App = {
    charts: {},
    socket: null,
    config: null,
    activeFilters: {},

    init: async function() {
        console.log("🚀 App Initializing...");
        
        try {
            console.log("📡 Fetching init data...");
            const initRes = await fetch('init');
            if (!initRes.ok) throw new Error(`Init API failed: ${initRes.status}`);
            const data = await initRes.json();
            this.config = data;
            console.log("✅ Init data received:", data);
            
            // Load template
            const templatePath = data.layout?.pageTemplate || 'public/templates/template_base.html';
            await this.loadTemplate(templatePath);
            
            console.log("🎨 Rendering components...");
            // Render content
            this.renderHighlights(data.highlights);
            this.renderCharts(data.charts);
            this.renderFilters(data.blocks);

            this.connectWS();
            console.log("✨ Dashboard Ready!");
            
            // Redraw on window resize
            window.addEventListener('resize', () => {
                Object.values(this.charts).forEach(c => c.resize());
            });

        } catch (e) {
            console.error("❌ Init failed:", e);
            const root = document.getElementById('app-root');
            if(root) root.innerHTML = `<div class="p-8 text-red-500 bg-red-50 border border-red-200 rounded-lg m-4">
                <h3 class="font-bold">Dashboard Load Error</h3>
                <p>${e.message}</p>
            </div>`;
        }
    },

    loadTemplate: async function(url) {
        console.log(`📥 Loading template from: ${url}`);
        // Add timestamp to prevent caching issues
        const cacheBuster = `?t=${Date.now()}`;
        const res = await fetch(url + cacheBuster);
        if(!res.ok) throw new Error(`Template not found: ${url}`);
        const html = await res.text();
        const root = document.getElementById('app-root');
        if(root) {
            // Handle full HTML document: extract body content
            let content = html;
            if (html.includes('<body')) {
                // Extract content inside body tag
                const bodyMatch = html.match(/<body[^>]*>([\s\S]*)<\/body>/i);
                if (bodyMatch) {
                    content = bodyMatch[1];
                } else {
                    // If no closing tag, try to extract content after body start
                    const bodyStartMatch = html.match(/<body[^>]*>([\s\S]*)/i);
                    if (bodyStartMatch) {
                        content = bodyStartMatch[1];
                    }
                }
            }
            
            root.innerHTML = content;
            
            // Execute scripts in the loaded template
            // When using innerHTML, <script> tags are not executed automatically
            const scripts = root.querySelectorAll('script');
            console.log(`📜 Found ${scripts.length} script(s) in template`);
            
            for (let i = 0; i < scripts.length; i++) {
                const oldScript = scripts[i];
                const scriptContent = oldScript.textContent;
                
                if (oldScript.src) {
                    // External script - load it
                const newScript = document.createElement('script');
                Array.from(oldScript.attributes).forEach(attr => {
                    newScript.setAttribute(attr.name, attr.value);
                });
                    await new Promise((resolve, reject) => {
                        newScript.onload = resolve;
                        newScript.onerror = reject;
                        oldScript.parentNode.insertBefore(newScript, oldScript);
                        oldScript.parentNode.removeChild(oldScript);
                    });
                } else {
                // Inline script - execute it directly
                try {
                    // Skip if it's not a JS script (e.g. application/json)
                    if (oldScript.type && oldScript.type !== 'text/javascript' && oldScript.type !== 'module') {
                        console.log(`⏩ Skipping non-JS script ${i + 1}/${scripts.length} (type: ${oldScript.type})`);
                        continue;
                    }

                    console.log(`📜 Executing inline script ${i + 1}/${scripts.length}...`);
                        // Use Function constructor to execute in global scope
                        const scriptFunc = new Function(scriptContent);
                        scriptFunc();
                        console.log(`✅ Script ${i + 1} executed successfully`);
                    } catch (error) {
                        console.error(`❌ Error executing script ${i + 1}:`, error);
                        // Still try to execute using eval as fallback
                        try {
                            eval(scriptContent);
                            console.log(`✅ Script ${i + 1} executed using eval`);
                        } catch (evalError) {
                            console.error(`❌ Eval also failed for script ${i + 1}:`, evalError);
                        }
                    }
                    // Remove the old script tag
                    oldScript.parentNode.removeChild(oldScript);
                }
            }
            
            // Give a small delay to ensure all global functions are registered
            await new Promise(resolve => setTimeout(resolve, 100));
            console.log('✅ Template scripts executed');
            console.log('✅ window.currentPalette available:', typeof window.currentPalette);
            console.log('✅ window.currentThemeName available:', typeof window.currentThemeName);
            console.log('✅ window.fetchRealData available:', typeof window.fetchRealData);
            console.log('✅ window.switchPage available:', typeof window.switchPage);
        }
    },

    renderCharts: function(chartsData) {
        // Get theme configuration (from template)
        const themeConfig = getThemeConfig();
        const palette = themeConfig.palette;
        const themeName = themeConfig.themeName;
        
        Object.entries(chartsData).forEach(([id, data]) => {
            const el = document.getElementById(id);
            if (!el) return;

            // Force fix height
            if (el.clientHeight < 20) {
                el.style.height = '300px'; 
                el.style.width = '100%';
                el.style.position = 'relative';
            }

            if (data.error) {
                el.innerHTML = `<div class="text-red-400 p-4">${data.error}</div>`;
                return;
            }

            let chart = this.charts[id];
            if (!chart) {
                // Use theme name registered in template, or use default theme if none
                chart = echarts.init(el, themeName || null);
                this.charts[id] = chart;
            }
            
            let finalOption = data.option || {};
            
            // Only apply styling if template provided theme configuration
            if (palette) {
                try {
                    // Try to extract core data for restructuring
                    const rawSeries = finalOption.series?.[0];
                    const rawXAxis = Array.isArray(finalOption.xAxis) ? finalOption.xAxis[0] : finalOption.xAxis;
                    const rawYAxis = Array.isArray(finalOption.yAxis) ? finalOption.yAxis[0] : finalOption.yAxis;

                    // Unified handling for all supported chart types
                    if (rawSeries) {
                        const type = rawSeries.type;

                        // 1. Basic charts (Bar/Line)
                        if ((type === 'bar' || type === 'line') && rawXAxis && rawXAxis.data) {
                            finalOption = {
                                grid: palette.grid,
                                tooltip: { ...palette.tooltip, trigger: 'axis' },
                                xAxis: {
                                    type: 'category',
                                    data: rawXAxis.data,
                                    ...palette.categoryAxis
                                },
                                yAxis: {
                                    type: 'value',
                                    ...palette.valueAxis
                                },
                                series: [{
                                    name: rawSeries.name || 'Value',
                                    type: type,
                                    data: rawSeries.data,
                                    smooth: true,
                                    showSymbol: false,
                                    symbol: 'circle',
                                    itemStyle: type === 'bar' ? { borderRadius: [4, 4, 0, 0] } : { borderWidth: 3 },
                                    areaStyle: type === 'line' ? { opacity: 0.1, color: new echarts.graphic.LinearGradient(0,0,0,1,[{offset:0,color:'rgba(79, 70, 229, 0.3)'},{offset:1,color:'rgba(79, 70, 229, 0.01)'}]) } : undefined
                                }]
                            };
                        }
                        // 2. Heatmap
                        else if (type === 'heatmap') {
                            const vMap = finalOption.visualMap || palette.visualMap;
                            finalOption = {
                                grid: palette.grid,
                                tooltip: { ...palette.tooltip, trigger: 'item' },
                                xAxis: {
                                    type: 'category',
                                    data: rawXAxis ? rawXAxis.data : [],
                                    ...palette.categoryAxis
                                },
                                yAxis: {
                                    type: 'category', // Heatmap Y-axis is also category
                                    data: rawYAxis ? rawYAxis.data : [],
                                    ...palette.categoryAxis
                                },
                                visualMap: { ...vMap, ...palette.visualMap },
                                series: [{
                                    ...rawSeries,
                                    itemStyle: palette.heatmap.itemStyle,
                                    label: palette.heatmap.label
                                }]
                            };
                        }
                        // 3. Boxplot
                        else if (type === 'boxplot') {
                             finalOption = {
                                grid: palette.grid,
                                tooltip: { ...palette.tooltip, trigger: 'item' },
                                xAxis: {
                                    type: 'category',
                                    data: rawXAxis ? rawXAxis.data : [],
                                    ...palette.categoryAxis
                                },
                                yAxis: {
                                    type: 'value',
                                    ...palette.valueAxis
                                },
                                series: [{
                                    ...rawSeries,
                                    itemStyle: palette.boxplot.itemStyle,
                                    emphasis: palette.boxplot.emphasis,
                                    boxWidth: palette.boxplot.boxWidth
                                }]
                            };
                        }
                        // 4. Pie chart
                        else if (type === 'pie') {
                            finalOption = {
                                tooltip: { ...palette.tooltip, trigger: 'item' },
                                legend: { ...palette.legend, bottom: 0 },
                                series: [{
                                    ...rawSeries,
                                    radius: ['40%', '70%'], // Force donut style
                                    itemStyle: { borderWidth: 2, borderColor: '#ffffff' },
                                    label: { show: false }
                                }]
                            };
                            // Pie charts don't need axes and grid
                            delete finalOption.xAxis;
                            delete finalOption.yAxis;
                            delete finalOption.grid;
                        }
                    }
                } catch (err) {
                    console.warn("Restyling failed", err);
                }
            }
            
            chart.setOption(finalOption, { notMerge: true });
            setTimeout(() => chart.resize(), 50);
        });
    },

    renderHighlights: function(list) {
        if (!list) return;
        list.forEach(item => {
            const titleEl = document.getElementById(`title-${item.id}`);
            const valEl = document.getElementById(`val-${item.id}`);
            const unitEl = document.getElementById(`unit-${item.id}`);
            
            if (titleEl) titleEl.textContent = item.title;
            if (valEl) valEl.textContent = item.value;
            if (unitEl && item.unit) unitEl.textContent = item.unit;
        });
    },

    renderFilters: function(blocks) {
      const container = document.getElementById('filter-container');
      if(!container) return;
      container.innerHTML = '';
  
      const filters = (blocks || []).filter(b => b.blockType === 'filter');
      filters.forEach(f => {
          const content = f.blockContent || {};
          const type = content.controlType;
          const field = content.field;
          const label = content.label || field;
          
          const wrap = document.createElement('div');
          wrap.className = "mb-6 border-b border-gray-100 pb-4 last:border-0";
          
          // Title
          wrap.innerHTML = `
              <label class="block text-xs font-bold text-gray-500 uppercase tracking-wider mb-3 flex items-center gap-1">
                  ${label}
              </label>
          `;
          
          // 1. Single Select (dropdown)
          if (type === 'select') {
              const selectWrap = document.createElement('div');
              selectWrap.className = "relative";
              // Color modification: focus:ring-[#E18182]
              selectWrap.innerHTML = `
                  <select class="block w-full pl-3 pr-8 py-2 text-sm border border-gray-200 bg-white rounded-lg focus:outline-none focus:ring-2 focus:ring-[#E18182] focus:border-transparent cursor-pointer hover:border-gray-300 transition-colors appearance-none">
                  </select>
                  <div class="absolute inset-y-0 right-0 flex items-center px-2 pointer-events-none text-gray-400">
                      <i class="ph ph-caret-down"></i>
              </div>
          `;
              const sel = selectWrap.querySelector('select');
              (content.options || []).forEach(opt => {
              const o = document.createElement('option');
              o.value = opt;
              o.textContent = opt;
              sel.appendChild(o);
          });
          
              sel.onchange = (e) => {
                  const val = e.target.value === 'All' ? null : e.target.value;
                  this.sendFilter(field, val, 'equals');
              };
              wrap.appendChild(selectWrap);
          }
          
          // 2. Multi Select (Checkbox list)
          else if (type === 'multiselect') {
              const checkWrap = document.createElement('div');
              checkWrap.className = "max-h-48 overflow-y-auto pr-1 scrollbar-thin scrollbar-thumb-gray-200 scrollbar-track-transparent space-y-2";
              
              const options = content.options || [];
  
              const updateCheckboxes = () => {
                  const checkedBoxes = checkWrap.querySelectorAll('input:checked');
                  const allCheckedVals = Array.from(checkedBoxes).map(cb => cb.value);
                  
                  let val = null;
                  if (allCheckedVals.includes('All')) {
                      val = null;
                  } else if (allCheckedVals.length === 0) {
                      val = null; 
                  } else if (allCheckedVals.length === options.filter(o => o !== 'All').length) {
                      val = null; 
                  } else {
                      val = allCheckedVals;
                  }
                  this.sendFilter(field, val, 'in');
              };
  
              options.forEach(opt => {
                  const id = `chk-${field}-${opt.replace(/\s+/g, '-')}`;
                  const item = document.createElement('div');
                  item.className = "flex items-start";
                  
                  // Only "All" is checked by default
                  const isChecked = (opt === 'All');
                  
                  // Color modification: text-[#E18182] focus:ring-[#E18182]
                  item.innerHTML = `
                      <div class="flex items-center h-5">
                          <input id="${id}" type="checkbox" value="${opt}" ${isChecked ? 'checked' : ''} class="w-4 h-4 text-[#E18182] border-gray-300 rounded focus:ring-[#E18182] cursor-pointer transition duration-150 ease-in-out">
                      </div>
                      <div class="ml-2 text-sm">
                          <label for="${id}" class="font-medium text-gray-700 cursor-pointer select-none">${opt}</label>
                      </div>
                  `;
                  const input = item.querySelector('input');
                  
                  input.onchange = (e) => {
                      const val = e.target.value;
                      const allChk = checkWrap.querySelector('input[value="All"]');
                      const otherChks = checkWrap.querySelectorAll('input:not([value="All"])');
  
                      if (val === 'All') {
                          if (input.checked) {
                              // When "All" is checked, uncheck all other options
                              otherChks.forEach(el => el.checked = false);
                          } else {
                              // If "All" is unchecked and no other option is selected, re-check "All"
                              const anyOtherChecked = Array.from(otherChks).some(el => el.checked);
                              if (!anyOtherChecked) {
                                  input.checked = true;
                              }
                          }
                      } else {
                          if (input.checked) {
                              // When other options are checked, uncheck "All"
                              if (allChk) allChk.checked = false;
                          } else {
                              // If an option is unchecked and no other option (including "All") is selected, re-check "All"
                              const anyChecked = Array.from(checkWrap.querySelectorAll('input')).some(el => el.checked);
                              if (!anyChecked && allChk) {
                                  allChk.checked = true;
                              }
                          }
                      }
                      updateCheckboxes();
                  };
                  
                  checkWrap.appendChild(item);
              });
              
              setTimeout(() => updateCheckboxes(), 0);
  
              wrap.appendChild(checkWrap);
          }
          
          // 3. Range / Slider (dual slider)
          else if (type === 'range' || type === 'slider') {
              const rangeWrap = document.createElement('div');
              rangeWrap.className = "space-y-4";
              const min = parseFloat(content.range?.min ?? 0);
              const max = parseFloat(content.range?.max ?? 100);
              const step = content.range?.step || (max - min) / 100;
              
              // Color modification: track bg-[#E18182], handle bg-[#E18182]
              rangeWrap.innerHTML = `
                  <div class="relative h-2 w-full mt-2">
                      <div class="absolute w-full h-1 bg-gray-200 rounded-full top-0.5"></div>
                      <div id="track-${field}" class="absolute h-1 bg-[#E18182] rounded-full top-0.5" style="left: 0%; right: 0%;"></div>
                      <div id="handle-min-${field}" class="absolute -top-1 w-4 h-4 rounded-full bg-[#E18182] shadow cursor-pointer pointer-events-none" style="left: -4px;"></div>
                      <div id="handle-max-${field}" class="absolute -top-1 w-4 h-4 rounded-full bg-[#E18182] shadow cursor-pointer pointer-events-none" style="right: -4px;"></div>
                      <input type="range" id="range-min-${field}" min="${min}" max="${max}" step="${step}" value="${min}" class="absolute w-full h-2 opacity-0 cursor-pointer pointer-events-none z-20 appearance-none [&::-webkit-slider-thumb]:pointer-events-auto [&::-webkit-slider-thumb]:w-4 [&::-webkit-slider-thumb]:h-4 [&::-webkit-slider-thumb]:rounded-full [&::-webkit-slider-thumb]:bg-transparent">
                      <input type="range" id="range-max-${field}" min="${min}" max="${max}" step="${step}" value="${max}" class="absolute w-full h-2 opacity-0 cursor-pointer pointer-events-none z-20 appearance-none [&::-webkit-slider-thumb]:pointer-events-auto [&::-webkit-slider-thumb]:w-4 [&::-webkit-slider-thumb]:h-4 [&::-webkit-slider-thumb]:rounded-full [&::-webkit-slider-thumb]:bg-transparent">
                  </div>
                  <div class="flex justify-between items-center gap-2 mb-2">
                      <input type="number" id="num-min-${field}" min="${min}" max="${max}" value="${min}" readonly class="w-20 px-2 py-1 text-xs border border-gray-200 rounded text-center bg-gray-50 text-gray-700 focus:outline-none appearance-none">
                      <span class="text-gray-300 text-xs">-</span>
                      <input type="number" id="num-max-${field}" min="${min}" max="${max}" value="${max}" readonly class="w-20 px-2 py-1 text-xs border border-gray-200 rounded text-center bg-gray-50 text-gray-700 focus:outline-none appearance-none">
                  </div>
              `;
              
            const rangeMin = rangeWrap.querySelector(`#range-min-${field}`);
            const rangeMax = rangeWrap.querySelector(`#range-max-${field}`);
            const numMin = rangeWrap.querySelector(`#num-min-${field}`);
            const numMax = rangeWrap.querySelector(`#num-max-${field}`);
            const track = rangeWrap.querySelector(`#track-${field}`);
            const handleMin = rangeWrap.querySelector(`#handle-min-${field}`);
            const handleMax = rangeWrap.querySelector(`#handle-max-${field}`);

            if (!rangeMin || !rangeMax || !numMin || !numMax || !track) {
                console.warn(`[renderFilters] Missing slider elements for field ${field}`);
                wrap.appendChild(rangeWrap);
                return;
            }

            const updateUI = () => {
                  let vMin = parseFloat(rangeMin.value);
                  let vMax = parseFloat(rangeMax.value);
  
                  if (vMin > vMax) {
                      const tmp = vMin; vMin = vMax; vMax = tmp;
                  }
  
                  numMin.value = Math.round(vMin * 10) / 10;
                  numMax.value = Math.round(vMax * 10) / 10;
  
                  const percentMin = ((vMin - min) / (max - min)) * 100;
                  const percentMax = ((vMax - min) / (max - min)) * 100;
  
                  track.style.left = percentMin + "%";
                  track.style.right = (100 - percentMax) + "%";
  
                  if (handleMin) {
                      handleMin.style.left = `calc(${percentMin}% - 8px)`;
                  }
                  if (handleMax) {
                      handleMax.style.left = `calc(${percentMax}% - 8px)`;
                  }
              };
  
              const getStepPrecision = (s) => {
                  const str = String(s);
                  if (str.indexOf('.') === -1) return 0;
                  return str.split('.')[1].length;
              };
              const precision = getStepPrecision(step);
  
              const normalizeVal = (v) => {
                  if (precision <= 0) return Math.round(v);
                  return parseFloat(v.toFixed(precision));
              };
  
              const debouncedSend = debounce(() => {
                  let vMin = parseFloat(numMin.value);
                  let vMax = parseFloat(numMax.value);
                  if (vMin > vMax) [vMin, vMax] = [vMax, vMin]; 
                  vMin = normalizeVal(vMin);
                  vMax = normalizeVal(vMax);
                  this.sendFilter(field, [vMin, vMax], 'between');
              }, 300);
  
              rangeMin.oninput = () => {
                  if(parseFloat(rangeMin.value) > parseFloat(rangeMax.value)) rangeMin.value = rangeMax.value;
                  updateUI();
                  debouncedSend();
              };
              rangeMax.oninput = () => {
                  if(parseFloat(rangeMax.value) < parseFloat(rangeMin.value)) rangeMax.value = rangeMin.value;
                  updateUI();
                  debouncedSend();
              };
              
              numMin.onchange = () => {
                  rangeMin.value = numMin.value;
                  updateUI();
                  debouncedSend();
              };
              numMax.onchange = () => {
                  rangeMax.value = numMax.value;
                  updateUI();
                  debouncedSend();
              };
  
              updateUI();
              wrap.appendChild(rangeWrap);
          }
          
          // 4. Date Range
          else if (type === 'date_range') {
                  const dateWrap = document.createElement('div');
                  dateWrap.className = "flex flex-col gap-2";
                  
                  const formatDate = (d) => {
                      if (!d) return '';
                      const normalized = String(d).replace(/\//g, '-');
                      const dt = new Date(normalized);
                      if (isNaN(dt.getTime())) return '';
                      return dt.toISOString().slice(0, 10);
                  };
                  
                  let minD = formatDate(content.range?.min);
                  let maxD = formatDate(content.range?.max);
                  if ((!minD || !maxD) && Array.isArray(content.options) && content.options.length > 0) {
                      const dateOpts = content.options.filter(o => o && o !== 'All').map(formatDate).sort();
                      if (dateOpts.length > 0) {
                          minD = minD || dateOpts[0];
                          maxD = maxD || dateOpts[dateOpts.length - 1];
                      }
                  }
  
                  // Color modification: focus:ring-[#E18182]
                  dateWrap.innerHTML = `
                  <div class="relative group">
                      <label class="text-[10px] text-gray-400 font-bold ml-1 mb-0.5 block">FROM</label>
                      <div class="relative">
                          <div class="absolute inset-y-0 left-0 pl-2.5 flex items-center pointer-events-none text-gray-400">
                              <i class="ph ph-calendar-blank"></i>
                          </div>
                          <input type="date" id="date-min-${field}" class="w-full pl-9 pr-3 py-1.5 text-sm border border-gray-200 rounded-lg bg-white focus:ring-2 focus:ring-[#E18182] focus:outline-none transition-shadow text-gray-700">
                      </div>
                  </div>
                  <div class="relative group">
                      <label class="text-[10px] text-gray-400 font-bold ml-1 mb-0.5 block">TO</label>
                      <div class="relative">
                          <div class="absolute inset-y-0 left-0 pl-2.5 flex items-center pointer-events-none text-gray-400">
                              <i class="ph ph-calendar-blank"></i>
                          </div>
                          <input type="date" id="date-max-${field}" class="w-full pl-9 pr-3 py-1.5 text-sm border border-gray-200 rounded-lg bg-white focus:ring-2 focus:ring-[#E18182] focus:outline-none transition-shadow text-gray-700">
                      </div>
                  </div>
                  `;
                  
                const dMin = dateWrap.querySelector(`#date-min-${field}`);
                const dMax = dateWrap.querySelector(`#date-max-${field}`);
                
                if (!dMin || !dMax) {
                    console.warn(`[renderFilters] Missing date elements for field ${field}`);
                    wrap.appendChild(dateWrap);
                    return;
                }

                if (minD) {
                      dMin.min = minD;
                      dMax.min = minD;
                      dMin.value = minD;
                  }
                  if (maxD) {
                      dMin.max = maxD;
                      dMax.max = maxD;
                      dMax.value = maxD;
                  }
  
                  const handleDate = () => {
                      const v1 = dMin.value;
                      const v2 = dMax.value;
                      if (v1 && v2) {
                          this.sendFilter(field, [v1, v2], 'between');
                      } else {
                          this.sendFilter(field, null, 'between');
                      }
                  };
                  
                  dMin.addEventListener('change', handleDate);
                  dMax.addEventListener('change', handleDate);
  
                  setTimeout(() => handleDate(), 0);
  
                  wrap.appendChild(dateWrap);
          }
  
          container.appendChild(wrap);
      });
  },

    sendFilter: function(field, val, op = 'equals') {
        if (val === 'All' || (Array.isArray(val) && val.length === 0)) val = null;
        if (val === null) {
            delete this.activeFilters[field];
        } else {
            this.activeFilters[field] = { operator: op, value: val };
        }

        if(this.socket && this.socket.readyState === WebSocket.OPEN) {
            this.socket.send(JSON.stringify({
                type: 'filter',
                filters: this.activeFilters
            }));
        }
    },

    connectWS: function() {
        const proto = location.protocol === 'https:' ? 'wss' : 'ws';
        const wsPath = location.pathname.endsWith('/') ? location.pathname + 'ws' : location.pathname + '/ws';
        this.socket = new WebSocket(`${proto}://${location.host}${wsPath}`);
        this.socket.onopen = () => {
            if (Object.keys(this.activeFilters).length > 0) {
                this.socket.send(JSON.stringify({
                    type: 'filter',
                    filters: this.activeFilters
                }));
            }
        };
        this.socket.onmessage = (e) => {
            try {
                const msg = JSON.parse(e.data);
                if(msg.type === 'update') {
                    this.renderCharts(msg.charts || {});
                    this.renderHighlights(msg.highlights || []);
                }
            } catch(err) { console.error(err); }
        };
    }
};

// Ensure initialization is triggered even when script is loaded dynamically
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => App.init());
} else {
    console.log("DOM already ready, initializing App immediately...");
    App.init();
}
