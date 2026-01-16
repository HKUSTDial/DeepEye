// 获取主题配置的辅助函数（从模板中获取或使用默认值）
function getThemeConfig() {
    // 从模板中获取主题配置（模板通过 window.currentPalette 和 window.currentThemeName 暴露）
    if (window.currentPalette && window.currentThemeName) {
        return {
            palette: window.currentPalette,
            themeName: window.currentThemeName
        };
    }
    // 回退到默认主题（如果模板未加载主题配置）
    return {
        palette: null,
        themeName: null
    };
}

// 防抖工具函数
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

    init: async function() {
        console.log("🚀 App Initializing...");
        
        try {
            console.log("📡 Fetching init data...");
            const initRes = await fetch('init');
            if (!initRes.ok) throw new Error(`Init API failed: ${initRes.status}`);
            const data = await initRes.json();
            this.config = data;
            console.log("✅ Init data received:", data);
            
            // 加载模板
            const templatePath = data.layout?.pageTemplate || 'public/templates/template_base.html';
            await this.loadTemplate(templatePath);
            
            console.log("🎨 Rendering components...");
            // 渲染内容
            this.renderHighlights(data.highlights);
            this.renderCharts(data.charts);
            this.renderFilters(data.blocks);

            this.connectWS();
            console.log("✨ Dashboard Ready!");
            
            // 窗口调整时重绘
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
        // 添加时间戳防止缓存问题
        const cacheBuster = `?t=${Date.now()}`;
        const res = await fetch(url + cacheBuster);
        if(!res.ok) throw new Error(`Template not found: ${url}`);
        const html = await res.text();
        const root = document.getElementById('app-root');
        if(root) {
            // 处理完整的 HTML 文档：提取 body 内容
            let content = html;
            if (html.includes('<body')) {
                // 提取 body 标签内的内容
                const bodyMatch = html.match(/<body[^>]*>([\s\S]*)<\/body>/i);
                if (bodyMatch) {
                    content = bodyMatch[1];
                } else {
                    // 如果没有闭合标签，尝试提取 body 开始后的内容
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
        // 获取主题配置（从模板中获取）
        const themeConfig = getThemeConfig();
        const palette = themeConfig.palette;
        const themeName = themeConfig.themeName;
        
        Object.entries(chartsData).forEach(([id, data]) => {
            const el = document.getElementById(id);
            if (!el) return;

            // 强制修复高度
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
                // 使用模板中注册的主题名称，如果没有则使用默认主题
                chart = echarts.init(el, themeName || null);
                this.charts[id] = chart;
            }
            
            let finalOption = data.option || {};
            
            // 只有在模板提供了主题配置时才应用样式
            if (palette) {
                try {
                    // 尝试提取核心数据进行重构
                    const rawSeries = finalOption.series?.[0];
                    const rawXAxis = Array.isArray(finalOption.xAxis) ? finalOption.xAxis[0] : finalOption.xAxis;
                    const rawYAxis = Array.isArray(finalOption.yAxis) ? finalOption.yAxis[0] : finalOption.yAxis;

                    // 统一处理所有支持的图表类型
                    if (rawSeries) {
                        const type = rawSeries.type;

                        // 1. 基础图表 (Bar/Line)
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
                        // 2. 热力图 (Heatmap)
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
                                    type: 'category', // 热力图 Y 轴也是类目
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
                        // 3. 箱型图 (Boxplot)
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
                        // 4. 饼图 (Pie)
                        else if (type === 'pie') {
                            finalOption = {
                                tooltip: { ...palette.tooltip, trigger: 'item' },
                                legend: { ...palette.legend, bottom: 0 },
                                series: [{
                                    ...rawSeries,
                                    radius: ['40%', '70%'], // 强制使用甜甜圈风格
                                    itemStyle: { borderWidth: 2, borderColor: '#ffffff' },
                                    label: { show: false }
                                }]
                            };
                            // 饼图不需要轴和网格
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
          
          // 标题
          wrap.innerHTML = `
              <label class="block text-xs font-bold text-gray-500 uppercase tracking-wider mb-3 flex items-center gap-1">
                  ${label}
              </label>
          `;
          
          // 1. Single Select (单选下拉)
          if (type === 'select') {
              const selectWrap = document.createElement('div');
              selectWrap.className = "relative";
              // 修改颜色：focus:ring-[#E18182]
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
          
          // 2. Multi Select (Checkbox 列表)
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
                  
                  // 默认只选中 "All"
                  const isChecked = (opt === 'All');
                  
                  // 修改颜色：text-[#E18182] focus:ring-[#E18182]
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
                              // 选中 "All" 时，取消选中其他所有选项
                              otherChks.forEach(el => el.checked = false);
                          } else {
                              // 如果取消选中 "All"，且没有其他选项被选中，则重新选中 "All"
                              const anyOtherChecked = Array.from(otherChks).some(el => el.checked);
                              if (!anyOtherChecked) {
                                  input.checked = true;
                              }
                          }
                      } else {
                          if (input.checked) {
                              // 选中其他选项时，取消选中 "All"
                              if (allChk) allChk.checked = false;
                          } else {
                              // 如果取消选中了一个选项，且没有任何其他选项（包括 "All"）被选中，则重新选中 "All"
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
          
          // 3. Range / Slider (双滑块)
          else if (type === 'range' || type === 'slider') {
              const rangeWrap = document.createElement('div');
              rangeWrap.className = "space-y-4";
              const min = parseFloat(content.range?.min ?? 0);
              const max = parseFloat(content.range?.max ?? 100);
              const step = content.range?.step || (max - min) / 100;
              
              // 修改颜色：轨道 bg-[#E18182]，手柄 bg-[#E18182]
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
          
          // 4. Date Range (日期范围)
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
  
                  // 修改颜色：focus:ring-[#E18182]
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
        if(this.socket && this.socket.readyState === WebSocket.OPEN) {
            // 处理 All 的情况
            if (val === 'All' || (Array.isArray(val) && val.length === 0)) val = null;
            
            // 构建 Filter 对象
            const filterObj = {};
            if (val !== null) {
                filterObj[field] = { operator: op, value: val };
            } else {
                // 发送空值以清除过滤器
                filterObj[field] = { operator: op, value: null };
            }

            this.socket.send(JSON.stringify({
                type: 'filter',
                filters: filterObj
            }));
        }
    },

    connectWS: function() {
        const proto = location.protocol === 'https:' ? 'wss' : 'ws';
        const wsPath = location.pathname.endsWith('/') ? location.pathname + 'ws' : location.pathname + '/ws';
        this.socket = new WebSocket(`${proto}://${location.host}${wsPath}`);
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

// 确保脚本动态加载时也能触发初始化
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => App.init());
} else {
    console.log("DOM already ready, initializing App immediately...");
    App.init();
}