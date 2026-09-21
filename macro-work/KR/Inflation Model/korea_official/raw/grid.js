var globalRowClickIndex = -1;
var globalRowClickTrIndex = -1;


/**
 * include_centerGrid.jsp 의 공통적인 js function 이동처리 
 */
$(document).ready(function(){		
	$stat_tab = $(".stat_tab", parent.document);
	// var tabNum = $(".stat_tab>ul>li[tabIndex]", parent.document).size();//탭번호
	 var tabNum = 0;
	 $(".stat_tab>ul", parent.document).find("li").each(function(index){
	  if($(this).hasClass("tab_on")) tabNum = index+1;
	 });
	
	if(parent.parent.iframe_leftMenu.temTblNm != '' && parent.parent.iframe_leftMenu.temTblNm != undefined) {
		try{
			if(parent.parent.iframe_leftMenu.temTblNm != g_tableNm){
				parent.fn_setTabTitle("ul>li.tab_on>a:first>div.tab_title", g_tableNm, tabNum, g_tableNm, $("#orgId").val(), g_tblId, g_tableNm);
			}else{
				parent.fn_setTabTitle("ul>li.tab_on>a:first>div.tab_title", g_tableNm, tabNum, parent.parent.iframe_leftMenu.temTblNm, $("#orgId").val(), g_tblId, g_tableNm);
			}
		} catch (e) {
			parent.fn_setTabTitle("ul>li.tab_on>a:first>div.tab_title", g_tableNm, tabNum, g_tableNm, $("#orgId").val(), g_tblId, g_tableNm);
		}
	} else {
		parent.fn_setTabTitle("ul>li.tab_on>a:first>div.tab_title", g_tableNm, tabNum, g_tableNm, $("#orgId").val(), g_tblId, g_tableNm);
	}
	
	 
//	$("#btnCloseAll", parent.document).text(closeAllText);
	
	top.document.title = g_tableNm;
	
	$btnCloseAll = $("#btnCloseAll", parent.document);
	//$btnCloseAll.text(g_closeAll);
	//$btnCloseAll.html("&nbsp;<img src='images/btn_tabon_close.png' title='전체닫기'>");

	var bodyWidth = $("body").width();
//	$("#modal").css("width", bodyWidth+"px")
//	$("#modal2").css("width", bodyWidth+"px")
//	$("#popup_outer").css("width", bodyWidth+"px")
//	$("#stat_box").css("width", bodyWidth+"px");
	
	var bodyHeight = $("#statHtmlBody").height();
	
	$("#iframe_centerMenu").css("height", bodyHeight+"px");	
	
	resizableHandler();
	
	fn_etcFunctionControll();
	
	$('html').click(function(e) {
		if(!$(e.target).hasClass("assayPopupBtn")) {
			$(".assayPopupBox").css("display", "none");
		}
	});
	$("#addFuncSet input, #addFuncSet select").focus(function(e) {
		$("#dataSearchBtn").addClass("off");
		$("#assayStartBtn").addClass("off");
	});
	
	$("#findDataSet input, #findDataSet select").focus(function(e) {
		$("#dataSearchBtn").removeClass("off");
		$("#assayStartBtn").addClass("off");
	});
	
	/*
	$("#chartOptionDiv").dialog({
		  autoOpen : false		
		, modal : false
		, resizable : false
		, maxWidth : 1024
		, maxHeight : 800
		, width : "700"
		, height : "550"
		, buttons : {
			"확인" : function(){}
			, Cancel : function(){
				$(this).dialog("close");
			}
		}
		, show : {
			effect : "blind"
			, duration : 1000
		}
		, hide : {
			effect : "explode"
			, duration : 1000
		}
	});
	*/
	
	
	$("#htmlGrid").bind("scroll", function(){
		if(g_trHeaderWidthResize == "DONE"){
 			//fn_tableFix();	 			
		}
	});
	
	
	//URL 생성페이지 불러오기
	$.ajax({
		type : 'POST',
		url : cf_getContextPath()+"/createUrl.do",
		dataType : "text",
		success : function(response,status){
			$("#popup_outer").append(response);
		},
		error : function(error){
		}
	});
});
	


//셀 병합
function fn_cellMerge(){
	
	//병합 초기화
	fn_cellUnmerge();
	
		//중복내용 셀 병합(하위레벨부터 병합실행) 			
	for(var idx = g_leftHeaderSize-1; idx >= 0; idx--){
		genRowSpan(idx);
	}
}

//셀 병합 초기화(링크 존재시 사라지는 문제 발생하여 사용안함)
function fn_cellUnmerge(){
	
		//모든셀 내용삽입 			
		var prevStr  = "";	//비교대상
		var currStr  = "";	//비교대상
		var prevHtml = "";	//복사대상
		var currHtml = "";	//복사대상			
		
		$("#mainTable tbody tr").each(function(){
			for(var i = 0 ; i < g_leftHeaderSize ; i++){
				prevStr = $(this).prev().find("td").eq(i).find("span:last").text();
				currStr = $(this).find("td").eq(i).find("span:last").text();
				
				prevHtml = $(this).prev().find("td").eq(i).html();
				currHtml = $(this).find("td").eq(i).html();
				
				if(prevStr == ""){
					prevHtml = currHtml;
				}
				
				if(currStr == "" ){
					$(this).find("td").eq(i).html(prevHtml);
				}
				
				$(this).find("td").eq(i).css("border", "1px solid #bbbbbb");//라인스타일추가	 					
			
			};
		});
}


//병합할 셀 내용 삭제
function genRowSpan(colIdx){
	var that; 
	var thatHtml; 
	$("#mainTable tbody tr").each(function(row) { 
		var currTdHtml = "";
		for(var i = 0; i <= colIdx; i++){
			currTdHtml += $('td:eq('+i+')', this).html();
		}
		
		var currTd = $('td:eq('+colIdx+')', this);		 

		if(currTdHtml == thatHtml){				
			$(currTd).text("");
			$(currTd).css("border-top","hidden");
			 
		}else{
			that = currTd;
			thatHtml = currTdHtml;
		}
	   
		that = (that == null) ? currTd : that; 
	});
}

function rowClick(){
	/*###########################################################
	#  	2021.09.14 주간보고 시 사무관님 기능 추가 요청 						    #
	# 		Cell 클릭 시 세로표시도 나올 수 있도록 기능 변경 요청 					#
	###########################################################*/
	
	$maintable = $("#mainTable");
	
	var tdIndex = $(event.target).closest("td").prevAll().length;
	globalRowClickIndex = tdIndex;
	globalRowClickTrIndex = $(this).closest("tr").prevAll().length;
	
	
	var isHeader = $maintable.find("tbody tr:eq("+globalRowClickTrIndex+")").find("td:eq("+tdIndex+")").hasClass("trHeader");
	
	if(isHeader) return;	//Header 표측은 클릭 이벤트를 발생시키지 않음.
	
	
	$maintable.find("tbody tr").removeClass("rowClick");
	$maintable.find("tbody tr").children().removeClass("rowClick");
	
	
	
	$(this).children().addClass("rowClick");
	
	$maintable.find("tbody tr").each(function(index, trs){
		$(trs).find("td:eq("+tdIndex+")").addClass("rowClick");
	});
	
	
	
	$("#copyTableDiv").find("tbody tr").removeClass("rowClick");
	$("#copyTableDiv").find("tbody tr").children().removeClass("rowClick");
	$("#copyTableDiv").find("tbody tr:eq("+globalRowClickTrIndex+")").children().addClass("rowClick");
	
	
	
}

//새 탭 열기
function fn_openNewTab() {
	parent.tabControll($('#orgId').val(), g_tblId, "", "", "", "", "", "");
}


//영문통계표 조회시 시점 월/분기 영문 표시 이벤트
function fn_language_change(){
	for(var i=0; i<g_result.length; i++){
		var tabId = g_result[i];					
		var tabText = "";
		
		if(tabId == "M"){
			tabText="월";
		}else if(tabId == "Q"){
			tabText="분기";
		}
		if(g_dataOpt == "en" || g_dataOpt == "cden"){
			if(tabId == 'M'){
				var mon_arry =["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
				
				$("#samePrdse_"+tabId).find("option").each(function(){
					var leftValue = this.value;
					if(leftValue != ''){
						if(leftValue == "all"){
							this.text = "all";
						}else{
							this.text = mon_arry[leftValue-1];
						}
					}
				});
			}else if(tabId == 'Q'){
				$("#samePrdse_"+tabId).find("option").each(function(){
					var leftValue = this.value;
					if(leftValue != ''){
						if(leftValue == "all"){
							this.text = "all";
						}else{
							this.text = leftValue + " Quarter";
						}
					}
				});				
			}else if(tabId == 'H'){
				var half_arry =["first Half", "latter Half"];
				$("#samePrdse_"+tabId).find("option").each(function(){
					var leftValue = this.value;
					if(leftValue != ''){
						if(leftValue == "all"){
							this.text = "all";
						}else{
							this.text = half_arry[leftValue-1];
						}
					}
				});
			}

			
		}else{
			if(tabId == 'M' || tabId == 'Q' || tabId == 'H'){

				var half_arry =["전반기", "후반기"];
				$("#samePrdse_"+tabId).find("option").each(function(){
					var leftValue = this.value;
					
					if(leftValue != ''){
						if(leftValue == "all"){
							if(tabId == 'M'){
								this.text = "매월";
							}else if(tabId == "Q"){
								this.text = "매분기";
							}else if(tabId == "H"){
								this.text = "매반기";
							}
							
						}else{
							if(tabId == 'H'){
								var leftValue = this.value;
								this.text = half_arry[leftValue-1];
							}else{
								this.text = leftValue + tabText;
							}
						}
					}
				});
			}			
		}
	}
}



/************************************************************************
함수명 : chartPrint()
설   명 : 차트다운로드 이벤트
 ************************************************************************/
function chartPrint(){
	
	var myForm = document.ParamInfo;
	var tabNum = top.$("#iframe_rightMenu").contents().find(".stat_tab>ul>li.tab_on").attr("tabindex");//탭번호
	//console.log("tabNum=",tabNum);
	var popwin = window.open("", "newWindow_"+tabNum, "toolbar=no, width=1200,height=800, scrollorbar=no");
	myForm.target = "newWindow_"+tabNum;
	myForm.action = cf_getContextPath()+"/openFullsizeChart.do?print=print&g_ChartGubun=" + g_ChartGubun;
	myForm.submit();	
	myForm.target = "_self";
	
	
	
	
	
	
	/*	
	var features = "menubar=no,toolbar=no,location=no,directories=no,status=no,scrollbars=yes,resizable=yes,width=1100,height=600,left=0,top=0";
	var printPage = window.open("about:blank", "",features);
	
	printPage.document.open();
	printPage.document.write("<html><head><title></title><style type='text/css'>body,tr,td,input,textarea{font-family:Tahoma;Font-size:9pt;}</style>\n</head>\n<body style='height:600px;width:1000px;'>"+Chartcontent.innerHTML+"<br>"+liClsNm.innerHTML+"\n</body></html>");
	printPage.document.close();
	printPage.print();
	*/
		
	
}



/************************************************************************
함수명 : chartDown()
설   명 : 차트이미지 다운로드 버튼 이벤트
 ************************************************************************/
function chartDown(){
	var format='JPG';
	var chartObj = FusionCharts(chartId);
	chartObj.exportChart({
		exportFormat: format
	});
};


/************************************************************************
함수명 : fn_timeAllSelect()
설   명 : 시점에서의 전체선택 및 해제
 ************************************************************************/
function fn_timeAllSelect(val){
	$('[name=timeChk'+val+']').each(function(index){
		if($("input:checkbox[id='selectAll"+val+"']").is(":checked")){
			if(!$(this).is(":checked")){
				$(this).prop('checked', true);
				fn_timeCountChk(this, val);
			}
		}else{
			if($(this).is(":checked")){
				$(this).prop('checked', false);
				fn_timeCountChk(this, val);
			}
		}
	});
}



/************************************************************************
함수명 : adjustThtmlGrid()
설   명 : ThtmlGrid 그리드 위치잡기
 ************************************************************************/
function adjustThtmlGrid(){
	var x = $("#htmlGrid").position().left + "px";
	var y = $("#htmlGrid").position().top + "px";
	
	/* 2017.11.06 항목,분류,시점에서 하단 스크롤바 이동후 조회시 틀고정 틀어지는 문제 수정 - 김경호  */
	if($("#htmlGrid").position().left < 0){
		x = "0px";				
	}
	
	$("#ThtmlGrid").css("left",x);	/* div 위치 잡기 */
//	$("#ThtmlGrid").css("top",y);	
	
	$("#ThtmlGrid").css("display","block");
	var mainTableT_H = $("#mainTableT").height();
	$("#ThtmlGrid").css("height",mainTableT_H);
	
	$("#ThtmlGrid").scrollLeft($("#htmlGrid").scrollLeft()); /* 통계표의 가로 스크롤 위치와 틀고정되는 표두와의 스크롤 위치를 다시 맞춰준다... */
	
	$(window).resize();
	$("#copyTableHeaderDiv").css("display","block");
	
}	







function pv_cellCssFormat(col_id){
	 var style = '';

	if(col_id == 'title'){
		style = 'style="background-color:#EEFFF5; font-weight:bold; color:#72777b;"';
	}else if(col_id.indexOf('tr')>-1){
		style = 'style="background-color:#FFFFF1;"';
	}else if(col_id.indexOf('ax')>-1){
		style = 'style="background-color:#FFFFF1;"';
	}
	return style;
}



function fn_chart2014(chartViewCnt){

	var tbl_id = 'tbl_data_view';
	var col_name_arrays = new Array();
	var col_model_arrays = new Array();

	$.each(g_remarkH,function(index,item){
		col_name_arrays.push(item.title);
		col_model_arrays.push({
			name : item.expression,
			index : item.expression,
			sortable: false,
			width : 150, aligh:'center',
			cellattr: function(){
				return pv_cellCssFormat(item.expression);
			}
		});
	});

	/* 2020.03.05 처음 로딩후에 계층컬럼구분같은 기능을 사용하여 컬럼명이 변경되었음에도 기존 컬럼명을 유지 하여 차트 범례가 안나오는 현상 수정 - 김경호 **/
	$('#'+tbl_id).jqGrid('GridUnload');
	
	$('#'+tbl_id).jqGrid({
		datatype: 'local',
		useColSpanStyle : true,
	   	colNames:col_name_arrays,
	   	colModel:col_model_arrays,
	   	scrollrows:true,
	   	height: 600,
	   	width : g_otherChartWidth,
	  	gridview: true,
		rowNum: -1,
		/* rowList: [5, 10, 20, 50], */
	   	loadonce: true,
        viewrecords: false,
		shrinkToFit: false,	/* 가로 넓이 맞춰서 데이터 출력 */
		sortable: false,
	   	loadui: false,		/* loading 표시안함  */
	    loadError:function(xhr, status, error){
	    	gfn_ajaxerror(error);
		},
		loadBeforeSend:function(data){
	    },
	   	gridComplete: function(){
	   	},
		loadComplete:function(data){
		}
	});
	gColNm = "";
	for(var i=0; i<col_name_arrays.length; i++){
		if(col_name_arrays[i] != ""){
    		if(i < col_name_arrays.length-1){
    			gColNm += col_name_arrays[i] + ","
    		}else{
    			gColNm += col_name_arrays[i]
  	    	}
		}
		
	}
	$("#clsNm").text(gColNm);
	var data_cnt = g_remarkB.length;
	/*  챠트보기 숫자 콤보박스에 선택된 값에 따라 출력해줘야 함 연동대기  */
	
	/* 2020.02.27 차트범례 누적으로 인한 범레 출력 오류 수정 - 김경호  */
	$("#tbl_data_view").jqGrid('clearGridData');
	
	for(var i=0; i<chartViewCnt;i++){
		var obj = g_remarkB[i];
		
		$("#tbl_data_view").jqGrid('addRowData',i,g_remarkB[i]);
		$("#"+i+" td:eq(0)").css("color","#"+g_chartColor[i]);
		$("#"+i+" td:eq(0)").css("text-align","center");
		$("#"+i).css("font-weight","bold");
		$("#"+i).css("background-color","#FFFFF1");
		/* ie 8 챠트 사각형 색상이 bottom 그려지는 현상 수정 */
		$("#"+i+" td").css("border-right","1px solid #000000");
		$("#"+i+" td").css("border-bottom","1px solid #000000");
	}

	//BYOH CSS 수정
	/*
	$("#popMode").css("visibility","hidden");
	$("#popMode").css("height","0px");
	$("#htmlGrid").css("margin-top","0");
	$("#htmlGrid").css("height","0px");
	*/
	
	$(".ui-jqgrid-bdiv").css("height","206px");
	//$("#Legend").css("topx","1px");
	//$("#Legend").css("height","70px");
	//$("#Legend").css("visibility","visible");
	/*  jqGrid 테두리  */
	$("#gbox_tbl_data_view").css("border-top,border-right","1px solid #b1b1b1");
	/* 범례 안내문 높이 지정 */
	$(".legend").css("margin-top","7px");
	/*  챠트 범례 jqGrid 수정 후 htmlGrid border 겹치는 현상으로 border 값 초기화 */
	
	//$("#htmlGrid").css("border","0px");
}

//tree 체크값 g_defaultClassArr g_classEachCnt적용
function fn_setDefaultClassArr(treeId) {
	var selectedNodes = $.ui.fancytree.getTree("#" + treeId).getSelectedNodes();

	//선택 된 값이 들어있는 배열 data 초기화, 없으면 빈배열 생성 후 추가
	for(var i=0; i<selectedNodes.length; i++) {
		var existTreeData = false;
		
		$.each(g_defaultClassArr,function(index,item){
			if(selectedNodes[i].data.objVarId == item.objVarId && selectedNodes[i].data.lvl == item.classType) {
				item.data = [];
				item.classLvlCnt = item.data.length;
				existTreeData = true;
			}
		});
		
		if(!existTreeData) {
			var tmpObj = {};
			tmpObj.classLvlCnt = 0;
			tmpObj.classType = selectedNodes[i].data.lvl;
			tmpObj.data = [];
			tmpObj.objVarId = selectedNodes[i].data.objVarId;
			g_defaultClassArr.push(tmpObj);
		}
		
	}
	
	//data 배열의 길이가 0이 아니면 선택안된 값이 저장되어있는 배열이므로 삭제, selectedNodes가 0이면 전체해제된 상태이므로 objVarId만 일치하면 삭제
	var j=0;
	
	while(j<g_defaultClassArr.length) {
		var existClassArr = true;
		
		if(selectedNodes.length == 0) {
			var delObjVarId = $.ui.fancytree.getTree("#" + treeId).getRootNode().children[0].data.objVarId;
			if(g_defaultClassArr[j].objVarId == delObjVarId) existClassArr = false;
		} else {
			for(var i=0; i<selectedNodes.length; i++) {
				if(selectedNodes[i].data.objVarId == g_defaultClassArr[j].objVarId && g_defaultClassArr[j].data.length > 0) existClassArr = false;
			}
		}
		
		if(!existClassArr) {
			g_defaultClassArr.splice(j, 1);
		} else {
			j++;
		}
	}
	
	//data 배열 채우기
	for(var i=0; i<selectedNodes.length; i++) {
		$.each(g_defaultClassArr,function(index,item){
			if(selectedNodes[i].data.objVarId == item.objVarId && selectedNodes[i].data.lvl == item.classType) {
				item.data.push(selectedNodes[i].data.itmId);
			}
			
			item.classLvlCnt = item.data.length;
		});
	}
	
	g_classCnt = 1;
	g_classViewCntStr = "";
	
	g_timeCnt = 0;
	for(var i=0; i<timeTreeList.length; i++) {
		g_timeCnt += $.ui.fancytree.getTree("#timeList" + timeTreeList[i]).getSelectedNodes().length;
	}
	
	for(var i=0; i<g_tabClassCnt.length; i++) {
		var length = $.ui.fancytree.getTree("#" + classTreeList[i]).getSelectedNodes().length;
		g_tabClassCnt[i].dataCnt = length;
		
		if($("#" + classTreeList[i]).css("display") != "none") {
			g_classCnt *= length;
			if( i == classTreeList.length-1) g_classViewCntStr += length;
			else g_classViewCntStr += (length) + "*";
			
			//g_classEachCnt 설정
			//tabClass.visible이 false인 tree정보는 g_classEachCnt에 없으므로 objVarId를 가지고 있는 g_tabClassCnt와 비교하여 dataCnt 설정
			for(var j=0; j<g_classEachCnt.length; j++) {
				if(g_classEachCnt[j].objVarId == g_tabClassCnt[i].objVarId) {
					g_classEachCnt[j].dataCnt = length;
					break;
				}
			}
		}
	}
	fn_countView(g_itmCnt,g_classCnt,g_timeCnt,g_classViewCntStr);
}

/************************************************************************
함수명 : fn_assay()
설   명 :  분석
 ************************************************************************/
function fn_assay(assayType){
	if(assayType =="TOTL_CMP_RATE" || assayType =="CMP_RATE" || assayType=="CHG_RATE_CO"){
		$("#assaySelectDiv").css("display", "block");
		//$("#assayBtnBeforeSelect").css("display", "none");
	}else{
		$("#assaySelectDiv").css("display", "none");
		//$("#assayBtnBeforeSelect").css("display", "flex");
	}
	var noselectType = null;
}



function notice_getCookie( name ){
	var nameOfCookie = name + "=";
	var x = 0;
	while ( x <= document.cookie.length )
	{
		var y = (x+nameOfCookie.length);
		if ( document.cookie.substring( x, y ) == nameOfCookie ) {
			if ( (endOfCookie=document.cookie.indexOf( ";", y )) == -1 )
				endOfCookie = document.cookie.length;
			return unescape( document.cookie.substring( y, endOfCookie ) );
		}
		x = document.cookie.indexOf( " ", x ) + 1;
		if ( x == 0 )
			break;
	}
	return "";
}



function fn_gridOpen(){

	$("#block"+g_hideId).css("display","none");
	$("#"+g_TabGubun).attr("class","menu_off");
	$("#textShow").hide();
	$("#btnShow").show();
	$("#stblUnit").show();
	$("#tailExplain").hide();
	$("#popMode").css("height","606px");
	$("#htmlGrid").css("height","604px");
	$("#htmlGrid").css("width","100%");			
	$("#Divchart").css("height","0");		
	//BYOH CSS 수정
	$("#popMode").css("visibility","visible");
	$("#popMode").css("display","block");
	g_flag = true;

	$("#changeAttribute").attr("class","cont_line");
	
	/*  2016.03.24 차트조회후 닫았을때 통계표 상단 틀고정 시작  */			
	adjustThtmlGrid();	/*  ThtmlGrid 위치조정  */
	/*  틀고정 끝  */
}




/*****
우측 부가정보 Div 가 숨겨져 있을 경우, 
	부가정보 Div Display, 
	숨김/보임 버튼 위치 조정 
*****/	 
function fn_settView(){
	$sett_box = $(".sett_box");
	$search_sett = $(".search_sett");
	
	if($sett_box.css('display') == "none"){
		fn_countView(g_itmCnt,g_classCnt,g_timeCnt,g_classViewCntStr);
		$sett_box.show();
		$search_sett.removeClass("search_sett_hide").addClass("search_sett_show");
		var rightPosition = $(".sett_box").width(); 
		$(".search_sett").css("right", rightPosition+"px");	
		$("#divSchset").focus();
    }else{
    	$sett_box.hide();        	
    	$search_sett.removeClass("search_sett_show").addClass("search_sett_hide").css("left", "");
    	$("#ico_querySetting").focus();
   	}
	
	if($(".assayPopupBox").css("display") != "none"){
		$(".assayPopupBox").css("display", "none");
    }
	
	if($("#pop_timeSet").css('display') != "none"){
		for(var i=0;i<g_result.length; i++){
			if(g_result[i] != 'Y'){
				$("#samePrdseYear_"+g_result[i]).val("").prop("selected",true);
	    		$("#samePrdse_"+g_result[i]).val("").prop("selected",true);
			}else{
				$("#samePrdseYear_"+g_result[i]).val("").prop("selected",true);
			}
		}
		g_timePopType=false;
		$("#pop_timeSet").hide(); 
	}
}

//tree 체크값 확인 후 selecteNodes 0인 경우 sett_view display
function fn_checkTreeReleaseAll() {
	var treeName = "";
	var timeCheck = false;
	
	$(".sett_box .list_box div").each(function(index){
		var treeId = $(this).attr("id");
		
		if($.ui.fancytree.getTree("#" + treeId).getSelectedNodes().length == 0) {
			if(treeId.indexOf("timeList") < 0) {
				treeName += $("#tab01 h3:eq(" + index + ") span font").attr("title") + ", ";
			}
		}
	});
	
	for(var i=0; i<timeTreeList.length; i++) {
		if($("#ico_chk_" + timeTreeList[i]).css("display") != "none") {
			timeCheck = true;
		}
	}
	
	if(!timeCheck) treeName += $("#tab01 h3:last span font").attr("title") + ", ";
	
	if(treeName != "") {
		treeName = treeName.substring(0, treeName.length - 2);
		alert(treeName + "이 선택되지 않았습니다.");
		return false;
	} else {
		return true;
	}
}

function resizableHandler(){
	var minWidth = 328;
	if(g_dataOpt == "en" || g_dataOpt == "cden") {
		minWidth = 420;
	} else {
		minWidth = 328;
	}
	
	$(".sett_box").resizable({
		handles : "w"
		, iframeFix : true
//		, alsoResize : "#sett_tab"
		, start : function(event, ui){				
		}
		, stop : function(event, ui){
			//$("#iframe_leftMenu").css("pointer-events", "auto");
		}
		, ghost : false
		, maxWidth : 1024
		, minWidth : minWidth
		, resize : function(event, ui){
			var thisLeft = parseInt($(this).css("left"));
			var search_sett_left = thisLeft - 19;
			$(this).css("right", "0px");
			
			//$(".search_sett").css("left", search_sett_left+"px");				
			$(this).css("left", "");
			
			var rightPosition = $(this).width(); 
			$(".search_sett").css("right", rightPosition+"px");	
		}
	});	
}

//scrollbar 유무
function fn_hasScrollBar(id) {
	return $("#" + id).prop("scrollHeight") > $("#" + id).prop("clientHeight");
}

//콤마삽입
function addComma(str){
	str = String(str);
	return str.replace(/(\d)(?=(?:\d{3})+(?!\d))/g,'$1,' );
}
//콤마제거
function removeComma(str){
	str = String(str);
	//return str.replace(/[^\d]+/g,'');
	return str.replace(/,/g,'');
}

function fn_browser(){
	var browser = (function() {
		  var s = navigator.userAgent.toLowerCase();

		  var match = /(chrome)[ \/](\w.]+)/.exec(s) ||
			  		  /(webkit)[ \/](\w.]+)/.exec(s) ||
		              /(opera)(?:.*version)?[ \/](\w.]+)/.exec(s) ||
		              /(msie) ([\w.]+)/.exec(s) ||
		              /(mozilla)(?:.*? rv:([\w.]+))?/.exec(s) ||
		             [];
		  return { name: match[1] || "", version: match[2] || "0" };
		}());

		var isIe11 = !!(navigator.userAgent.match(/Trident/)&& navigator.userAgent.match(/rv:11.0/));

		if(browser.name == 'msie'){
			gr_browser="ie";
			g_browserVersion = browser.version;
		}
}


/************************************************************************
함수명 : fn_tabWidth()
설   명 : tabMenu li width값 동적세팅	추후 사이즈값 조절
 ************************************************************************/
function fn_tabWidth(){
	var liCnt = $('.selection1 li').size();

	var divisionCnt;
	divisionCnt = 586/liCnt;
	atextCnt = divisionCnt - 20;
	if(liCnt>4){
		//통계표조회 버튼이 tabMenu로 이동 20131217 넓이 83
		var lastBgWidth = 852 - 820 + (liCnt*6) +15;

		$('.selection1 li').each(function(index){
			$(this).css("width",divisionCnt);
			$(this).find('a').css("width",atextCnt);
		});
	}else{
		var lastBgWidth = 852 - (180*liCnt) + (liCnt*5) +15;

		$('.selection1 li').each(function(index){
			$(this).css("width","137px");
			$(this).find('a').css("width","120px");
		});
	}
}

function fn_classStrView(p_classEachCnt){
	var p_classEachCntLength = p_classEachCnt.length-1;
	g_classViewCntStr ="";
	$.each(p_classEachCnt,function(index,item){
		if(index == p_classEachCntLength){
			g_classViewCntStr += item.dataCnt;
		}else {
			g_classViewCntStr += item.dataCnt+"*";
		}
	});
}


/************************************************************************
함수명 : fn_timeCountChk(timeCountObj,searchType)
설   명 : 시점탭에서 체크이벤트 함수(체크 true false 확인 후 count계산
인   자 : 1.checkbox = 선택된 object 객체
		 2.searchType
 ***********************************************************************/
function fn_timeCountChk(timeCountObj,searchType){
	var timeChkFlag = $(timeCountObj).is(":checked");
	if(timeChkFlag == true){
		timeCal = g_timeCnt + 1;
	}else{
			timeCal = g_timeCnt - 1;
	}
	g_timeCnt = timeCal;
	fn_countView(g_itmCnt,g_classCnt,g_timeCnt,g_classViewCntStr);
}

//정렬 신규추가(스크립트에서 처리)		
function fn_sortSearch(colIdx, type, obj){
	$(parent.parent.LoadingMsg).html("");
	colIdx = $(obj).closest("th").index();//화면에 보이는 index 순서대로처리
	
	//행 1개 정렬 무시
	if(g_tblRowCnt <= 1) return;
	
	fn_progressBar('show');
	setTimeout(function () { //progressBar 안보이는 현상 보완하고자 setTime사용
		fn_sortImg(colIdx, type);	//1. 정렬 오름, 내림차순 이미지 표시
		fn_cellUnmerge();			//2. 정렬시 좌측 타이틀 영역 셀병합 초기화
		fn_sortData(colIdx, type);	//3. 정렬								
		//fn_tableFix();		//4. 좌측 타이틀 고정
		$("#htmlGrid").animate({scrollTop :$("#htmlGrid").offset()},0);//정렬후 스크롤 상단으로 이동
		$("#mainTable").children("tbody").children("tr").removeClass("rowClick");//선택ROW 배경색 초기화
		fn_progressBar('hide');
		
		$("#ordColIdx").val(colIdx);
		$("#ordType").val(type);
	}, 50);
	
}

//데이터 정렬(정렬 우선순위 : 1-선택 칼럼, 2-좌측고정칼럼의 상위레벨부터 정렬)
function fn_sortData(colIdx, type){			
	
	fn_tableRelease();
	
	var buildType = $("#mainTable tbody tr").get();
	
	//선택한 칼럼 정렬 전 좌측 타이틀 선 정렬
	for(var i = g_leftHeaderSize - 1; i >= 0; i--){
		if(i != colIdx){
			buildType.sort(function (a, b){
				var sort1 = Number( $(a).find("td").eq(i).attr("sortsn") );
				var sort2 = Number($(b).find("td").eq(i).attr("sortsn") );

				return (sort1 < sort2)? -1 : (sort1 > sort2)? 1 : 0;//현재 정렬 타이틀 이외의 타이틀은 오름차순(1,2,3...)
			});
		}
	}
	
	//선택한 칼럼 정렬
	buildType.sort(function (a, b){			
		var val1 = $(a).find("td").eq(colIdx).find("span:last").text();
		var val2 = $(b).find("td").eq(colIdx).find("span:last").text();
		var sort1, sort2;
		
		if(val1.indexOf("(") > -1) {
			val1 = val1.substr(0, val1.indexOf("(")-1) 
		}
		
		if(val2.indexOf("(") > -1) {
			val2 = val2.substr(0, val2.indexOf("(")-1) 
		}
		 
		//if($.trim(val1) == "X"){val1 = null;}
		//if($.trim(val2) == "X"){val2 = null;}
		
		//숫자일경우 Number변환후 비교
		if( $.isNumeric(removeComma(val1)) && $.isNumeric(removeComma(val2)) ){
			val1 = Number(removeComma( val1 ));//다음값					
			val2 = Number(removeComma( val2 ));//이전값
		}				
						
		if(type == "0"){	//0 오름차순				
			return (val1 < val2)? -1 : (val1 > val2)? 1 : 0;//큰값이 위로
		}else{				//1 내림차순
			return (val2 < val1)? -1 : (val2 > val1)? 1 : 0;//작은값이 위로
		}
	});
	
	//정렬내용 append
	$.each(buildType, function (index, row){
		$("#mainTable tbody").append(row);	
	});
	if(!g_tableReleaseChk){
		fn_tableFix();
	}
	
}

function fn_pop_pivotfunc(){

	if($("#pop_pivotfunc").css('display') == "none"){
		$("#pop_pivotfunc").show();
		$("#pop_pivotfunc").css("z-index", "2");
	}else{
		$("#pop_pivotfunc").hide();
	}
}
//21.06.28 시점 팝업 레이어
function fn_timeSet(type){
	$sett_box = $(".sett_box");
	$search_sett = $(".search_sett");
    if($("#pop_timeSet").css('display') == "none"){
    	
    	if($(".assayPopupBox").css("display") != "none"){
    		$(".assayPopupBox").css("display", "none");
        }
    	
        if($sett_box.css('display') != "none"){
        	if(fn_checkTreeReleaseAll()) {
        		$sett_box.hide();        	
            	$search_sett.removeClass("search_sett_show").addClass("search_sett_hide").css("left", "");
            	    	 
        		$(".search_sett").css("right", "5px");
        	} else {
        		return;
        	}
        }
    	
    	fn_language_change();
    	for(var i=0;i<g_result.length; i++){
    		//$("#samePrdseYear_"+g_result[i]).val("").prop("selected",true);
    		//$("#samePrdse_"+g_result[i]).val("").prop("selected",true);
    		
    		fn_time_pop_list_set(g_result[i]);
    		g_defaultTabType = g_result[0];
    		fn_set_all_chk("timePopList"+g_result[i]);
    		fn_chk_prd(g_result[i]);
    	}

    	fn_detailPopSelect(g_defaultTabType,0);
    	g_timePopType = true;
    	fn_countView(g_itmCnt,g_classCnt,g_timeCnt,g_classViewCntStr);
        $("#pop_timeSet").show();
        $("#pop_timeSet").css("z-index", "2");
        if($("#downPopBtn").css("display") != "none"){
			$("#btnTimeDown").focus();
		}else{
			$("#btnTimeAccept").focus();
		}
    }else{
    	fn_countView(g_itmCnt,g_classCnt,g_timeCnt,g_classViewCntStr);
   	   g_timePopType = false;
       $("#pop_timeSet").hide();
       $("#btn_time").focus();
    }
}

function fn_etcFunctionControll(){
	
	$lis = $("#sett_tab>ul>li");
	$lis.off("click");
	
	$lis.each(function(index, li){	
		$(li).on("click", function(){
			var dataTab = $(li).attr("data-tab");
			
			fn_functionControllByItmKd(this, dataTab);
		});					
	});
}

function fn_functionControllByItmKd(li, dataTab) {
	if($(li).hasClass("active")) {
		$sett_box = $(".sett_box");
		$search_sett = $(".search_sett");
		if($sett_box.css('display') != "none"){
			if(fn_checkTreeReleaseAll()) {
				$sett_box.hide();        	
		       	$search_sett.removeClass("search_sett_show").addClass("search_sett_hide").css("left", "");
		       	    	 
		     	$(".search_sett").css("right", "5px");
		     	$("#ico_querySetting").focus();
			} else {
		     	return;
			}
		}
	} else {
		$("#sett_tab>ul>li").removeClass("active");
		$("#sett_tab>ul>li").removeClass("off");

		$lis.not($(li)).addClass("off");
		$(li).addClass("active");
		
		$(".sett_box .sett_cont[id='"+dataTab+"']").addClass("active");
		$(".sett_box .sett_cont[id!='"+dataTab+"']").removeClass("active");
		fn_setAssayPopupDisplay();
	}
}

function fn_xAxisControll(){
	
	$button = $(event.target);
	
	var status = $button.data("status");
	
	if(status == undefined || status == "0"){

		//테이블 고정
		fn_tableFix();
		g_tableReleaseChk = false;
	}else{		
		//테이블 고정 해제 
		fn_tableRelease();
		g_tableReleaseChk = true;
	}
}

//좌측 칼럼 틀고정 - (구) fn_leftTitleColFix() --호부장님 버전
function fn_tableFix_old(){
	
	var agent = navigator.userAgent.toLocaleLowerCase();
	
	var chrome = false;
	var edg = false;
	
	if(agent.indexOf("edg") != -1){
		edg = true;
	}else if(agent.indexOf("edge") != -1){
		edg = true;		
	}else if(agent.indexOf("chrome") != -1){
		chrome = true;
	}
	
	
	fn_tableRelease();
	
	$button = $("#btn_xAxis");	
	$button.data("status", "1");
	$button.attr("alt", xAxisRelease).attr("title", xAxisRelease).text(xAxisRelease);
	
	
	
	var divHeight = $("#htmlGrid").height() - 17;	
	var tableTop = parseInt($("#ThtmlGrid").css("top"))+"px";
	
	if(chrome){
		tableTop = parseInt($("#ThtmlGrid").css("top"))+1+"px";
	}
	
	//1.좌측 틀고정 하단 복사
		$tableCopy = $("#htmlGrid #mainTable").clone();
		var tableHeaderOrg = $("#htmlGrid #mainTable thead tr");
		
		$tableCopy.attr("id", "copyMainTable");
	
		$tableCopy.find("thead tr").each(function(trIndex, tr){
			var trHeight= $(tableHeaderOrg[trIndex]).height();
			$(tr).css("height", trHeight);
	
		    $(tr).find("th").each(function(tdIndex, th){
		       if(!$(th).hasClass("rowHead") && !$(th).hasClass("sortRowHead")){
		          $(th).remove();
		       }
		    });
		});
	
		//불필요한부분 제거
		$tableCopy.find("colgroup col").each(function(colIndex, col){	    
		    if(!$(col).hasClass("Selectable1")){
		        $(col).remove();
		    }
		});
	
		var tableBodyOrg = $("#htmlGrid #mainTable tbody tr");
		$tableCopy.find("tbody tr").each(function(trIndex, tr){
			var trHeight= $(tableBodyOrg[trIndex]).height();	
			$(tr).css("height", trHeight);
			
			//불필요한부분 제거
		    $(tr).find("td").each(function(tdIndex, td){
		       if(!$(td).hasClass("trHeader")){
		          $(td).remove();
		       }
		    });
		});
		
		var copyTableDiv = '<div id="copyTableDiv" style="left:0px;position: absolute;overflow-y: hidden;height:calc(100% - 19px);overflow:hidden;"></div>';
		$("#htmlGrid").append(copyTableDiv);
		$("#copyTableDiv").append($tableCopy);	
	
	//2.좌측 틀고정 상단 복사
		$mainTableHeader = $("#ThtmlGrid #mainTableT").clone();
		$mainTableHeader.attr("id", "copyMainTableT");
	
		//불필요한부분 제거
		$mainTableHeader.find("thead tr").each(function(trIndex, tr){
			var trHeight= $(tableHeaderOrg[trIndex]).height();
			//console.log("trHeight=="+trHeight);
			$(tr).css("height", trHeight);
	
		    $(tr).find("th").each(function(tdIndex, th){
		       if(!$(th).hasClass("rowHead") && !$(th).hasClass("sortRowHead")){
		          $(th).remove();
		       }
		    });
		});
		
		$mainTableHeader.find("colgroup col").each(function(colIndex, col){	    
		    if(!$(col).hasClass("Selectable1")){
		        $(col).remove();
		    }
		});
	
		$mainTableHeader.find("tbody tr").each(function(trIndex, tr){
		    $(tr).find("td").each(function(tdIndex, td){
		       if(!$(td).hasClass("trHeader")){
		          $(td).remove();
		       }
		    });
		});
	
		//복사내용 삽입
		var copyTableHeaderDiv = '<div id="copyTableHeaderDiv" style="left:0px;position: absolute;z-index:1; overflow:hidden;"></div>';
		$("#htmlGrid").append(copyTableHeaderDiv);
		$("#copyTableHeaderDiv").append($mainTableHeader);
	
		/*if(g_chartActive == "Y"){//정렬후 차트볼때 좌측타이틀 보이는 문제 처리
			$("#copyTableHeaderDiv").css("display","none");
		}else{
			$("#copyTableHeaderDiv").css("display","block");
		}
		
		//타이틀 위아래 스크롤시 본문도 함께 스크롤(스크롤 숨겼기때문에 무의미-동작안함)
		$("#copyTableDiv").bind("scroll", function(){
			var scrollTop = $(this).scrollTop();
			$("#htmlGrid").scrollTop(scrollTop);
		});*/
	
	//본문표 위아래 스크롤시 타이틀도 함께 스크롤
	$("#htmlGrid").bind("scroll", function(){
		var scrollTop = $(this).scrollTop();
		$("#copyTableDiv").scrollTop(scrollTop);
	});	
	
	$("#htmlGrid").scrollTop(0);
	
	g_leftThWidth = $("#copyMainTableT").width();//열고정시 좌측 타이틀 폭 세팅
	
	$(window).resize();
}

//좌측 칼럼 틀고정 - 엣지버그 개선 NEW TEST !!!!!!!!!!!!!
function fn_tableFix(){
	
	g_trHeaderWidthResize = "";
	
	$maintable = $("#mainTable"); 
	
	$maintable.find("tbody tr").removeClass("rowClick");
	$maintable.find("tbody tr").children().removeClass("rowClick");
	
	
	var agent = navigator.userAgent.toLocaleLowerCase();

	var chrome = false;
	var edg = false;

	if(agent.indexOf("edg") != -1){
		edg = true;
	}else if(agent.indexOf("edge") != -1){
		edg = true;
	}else if(agent.indexOf("chrome") != -1){
		chrome = true;
	}

	fn_tableRelease();

	$button = $("#btn_xAxis");
	$button.data("status", "1");
	$button.attr("alt", xAxisRelease).attr("title", xAxisRelease).text(xAxisRelease);

	var divHeight = $("#htmlGrid").height() - 17;
	var tableTop = $("#ThtmlGrid").css("top");
	
	//1.좌측 틀고정 copyTableDiv 복사
		$tableCopy = $("#htmlGrid #mainTable").clone();
		var tableHeaderOrg = $("#htmlGrid #mainTable thead tr");
		$tableCopy.attr("id", "copyMainTable");
		
		$tableCopy.find("thead tr").each(function(trIndex, tr){		
			var trHeight= $(tableHeaderOrg[trIndex])[0].getBoundingClientRect().height;
//			var trHeight= $(tableHeaderOrg[trIndex]).height();
			
			//----------------(body포함)표두명칭(fn_YAxisCreation) 없을때-------------
//			if(edg){
//				trHeight = trHeight - 1;//edge는 기본높이에서 -1 해야 크롬과 동일하게 보임				
//				if( !$("#mainTable thead tr:eq(0) th:eq("+g_leftHeaderSize+")").hasClass("titleHeader") ){ //표두명칭 칼럼 없을시				
//					var rowspanVal = $(tableHeaderOrg[trIndex]).find("th.rowHead").attr("rowspan")
//					if(rowspanVal > 1 && $(tableHeaderOrg[trIndex]).find("th.rowHead").not("th.titleHeader").text() != ""){
//						//console.log("(body포함)표두명칭 없음 높이증가("+(rowspanVal-1)+") trHeight="+trHeight+"	rowspanVal="+rowspanVal+ "	text="+ $(tableHeaderOrg[trIndex]).find("th.rowHead").text());
//						$(tr).css("height", trHeight + (rowspanVal-1));
//					}else{
//						//console.log("(body포함)표두명칭 없음 높이동일 trHeight="+trHeight+"	rowspanVal="+rowspanVal+ "	text="+ $(tableHeaderOrg[trIndex]).find("th.rowHead").text());
//						$(tr).css("height", trHeight);
//					}					
//				}				
//			}else{
//				$(tr).css("height", trHeight);
//			}			
			$(tr).css("height", trHeight);
			//--------------------------------------------------------
			
		    $(tr).find("th").each(function(tdIndex, th){
		       if(!$(th).hasClass("rowHead") && !$(th).hasClass("sortRowHead")){
		          $(th).remove();
		       }
		    });
		});
		
		//----------------(body포함)표두명칭(fn_YAxisCreation) 있을때-------------
//		if(edg){
//			if($("#mainTable thead tr:eq(0) th:eq("+g_leftHeaderSize+")").hasClass("titleHeader")){ //표두명칭 칼럼 존재시
//				$tableCopy.find("thead").find("tr").not("tr:last").each(function(trIndex, tr){
//					var tempHeight = $("#mainTable thead tr:eq("+trIndex+")").height() - 1;
//					//console.log("(body포함)표두명칭존재 text=" + $(tr).find("th:eq("+g_leftHeaderSize+")").text()+"	tempHeight=" + tempHeight);
//					if(tempHeight > 21){
//						$(tr).height( tempHeight + 1 );
//					}else{
//						$(tr).height( tempHeight );
//					}
//				});				
//			}
//		}
		//--------------------------------------------------------
		
		//불필요한부분 제거
		$tableCopy.find("colgroup col").each(function(colIndex, col){
		    if(!$(col).hasClass("Selectable1")){
		        $(col).remove();
		    }
		});

		var tableBodyOrg = $("#htmlGrid #mainTable tbody tr");
		$tableCopy.find("tbody tr").each(function(trIndex, tr){
			var trHeight= $(tableBodyOrg[trIndex])[0].getBoundingClientRect().height;
			var tmpText = $(tr).find("td:eq("+(g_leftHeaderSize-1)+") span:last").text();
			
			if(tmpText.trim() == "" || trHeight > 21){
				//console.log("       trIndex="+trIndex+"		trHeight="+trHeight+"		tmpText="+tmpText)
				$(tr).css("height", trHeight);
			}

		    $(tr).find("td").each(function(tdIndex, td){
		       if(!$(td).hasClass("trHeader")){
		          $(td).remove();
		       }
		    });
		});

		//복사내용 삽입
		var scroll_size = "";
		if(g_mobChk == 'true'){
			scroll_size = "1px";
		}else{
			scroll_size = "19px";
		}
		var copyTableDiv = '<div id="copyTableDiv" class="inner" style="left:0px;border:1px solid rgb(177, 177, 177); border-right:1px; border-bottom:1px; position:absolute; height:calc(100% - ' + scroll_size + '); overflow:auto; -ms-overflow-style:none; scrollbar-width:none;"></div>';
		$("#popMode").append(copyTableDiv);
		$("#copyTableDiv").append($tableCopy);
		if($("#popMode").width()>$tableCopy.width()){
			$("#copyTableDiv").width($tableCopy.width());//폭 조절
		}else{
			fn_tableRelease();
			fn_progressBar('hide');
			return;
		}

	//2.좌측 틀고정 copyTableHeaderDiv 복사		
		$mainTableHeader = $("#htmlGrid #mainTable").clone();
		$mainTableHeader.attr("id", "copyMainTableT");

		//바디 제거
		$mainTableHeader.find("tbody").remove();

		$mainTableHeader.find("thead tr").each(function(trIndex, tr){
			var trHeight= $(tableHeaderOrg[trIndex])[0].getBoundingClientRect().height;
			
			
			//----------------(header만)표두명칭(fn_YAxisCreation) 없을때-------------
//			if(edg){
//				trHeight = trHeight - 1;//edge는 기본높이에서 -1 해야 크롬과 동일하게 보임				
//				if( !$("#mainTable thead tr:eq(0) th:eq("+g_leftHeaderSize+")").hasClass("titleHeader") ){ //표두명칭 칼럼 없을시				
//					var rowspanVal = $(tableHeaderOrg[trIndex]).find("th.rowHead").attr("rowspan")
//					if(rowspanVal > 1 && $(tableHeaderOrg[trIndex]).find("th.rowHead").not("th.titleHeader").text() != ""){
//						//console.log("(header만)표두명칭 없음 높이증가("+(rowspanVal-1)+") trHeight="+trHeight+"	rowspanVal="+rowspanVal+ "	text="+ $(tableHeaderOrg[trIndex]).find("th.rowHead").text());
//						$(tr).css("height", trHeight + (rowspanVal-1));
//					}else{
//						//console.log("(header만)표두명칭 없음 높이동일 trHeight="+trHeight+"	rowspanVal="+rowspanVal+ "	text="+ $(tableHeaderOrg[trIndex]).find("th.rowHead").text());
//						$(tr).css("height", trHeight);
//					}					
//				}				
//			}else{
//				$(tr).css("height", trHeight);
//			}			
			$(tr).css("height", trHeight);
			//--------------------------------------------------------

		    $(tr).find("th").each(function(tdIndex, th){
		       if(!$(th).hasClass("rowHead") && !$(th).hasClass("sortRowHead")){
		          $(th).remove();
		       }
		    });
		});
		
		//----------------(header만)표두명칭(fn_YAxisCreation) 있을때-------------
//		if(edg){
//			if($("#mainTable thead tr:eq(0) th:eq("+g_leftHeaderSize+")").hasClass("titleHeader")){ //표두명칭 칼럼 존재시
//				$mainTableHeader.find("thead").find("tr").not("tr:last").each(function(trIndex, tr){
//					var tempHeight = $("#mainTable thead tr:eq("+trIndex+")").height() - 1;
//					//console.log("(header만)표두명칭존재 text=" + $(tr).find("th:eq("+g_leftHeaderSize+")").text()+"	tempHeight=" + tempHeight);
//					if(tempHeight > 21){
//						$(tr).height( tempHeight + 1 );
//					}else{
//						$(tr).height( tempHeight );
//					}
//				});				
//			}
//		}
		//--------------------------------------------------------
		
		//불필요한부분 제거
		$mainTableHeader.find("colgroup col").each(function(colIndex, col){
		    if(!$(col).hasClass("Selectable1")){
		        $(col).remove();
		    }
		});

		//복사내용 삽입
		var copyTableHeaderDiv = '<div id="copyTableHeaderDiv" class="inner" style="left:0px;border:1px solid rgb(177, 177, 177); border-right:1px; border-bottom:1px; position:absolute; overflow-y:hidden; height:'+divHeight+'px; overflow:hidden;"></div>';
		$("#popMode").append(copyTableHeaderDiv);
		$("#copyTableHeaderDiv").append($mainTableHeader);
		if($("#popMode").width()>$mainTableHeader.width()){
			$("#copyTableHeaderDiv").width($mainTableHeader.width());	//폭 조절
		}else{
			fn_tableRelease();
			fn_progressBar('hide');
			return;
		}
		$("#copyTableHeaderDiv").height($mainTableHeader.height());	//높이 조절
	//본문표 위아래 스크롤시 타이틀도 함께 스크롤
	$("#copyTableDiv").bind("scroll", function(){
		var scrollTop = $(this).scrollTop();
		$("#htmlGrid").scrollTop(scrollTop);
		if($(this).scrollTop()!=$("#htmlGrid").scrollTop()){
			$(this).scrollTop($("#htmlGrid").scrollTop());
		}
	});

	$("#htmlGrid").bind("scroll", function(){
		var scrollTop = $(this).scrollTop();
		$("#copyTableDiv").scrollTop(scrollTop);
	});

	$("#htmlGrid").scrollTop(0);

	g_leftThWidth = $("#copyMainTableT").width();//열고정시 좌측 타이틀 폭 세팅

	$(window).resize();
	
	if(globalRowClickTrIndex > -1){
		$("#copyTableDiv").find("tbody tr:eq("+globalRowClickTrIndex+")").children().addClass("rowClick");		
		$maintable.find("tbody tr:eq("+globalRowClickTrIndex+")").children().addClass("rowClick");		
	}
	
	if(globalRowClickIndex > -1){
		$("#mainTable, #copyMainTable").find("tbody tr").each(function(index, trs){
			$(trs).find("td:eq("+globalRowClickIndex+")").addClass("rowClick");
		});
	}	
	//console.timeEnd("fn_tableFix");
	fn_progressBar('hide');
}

function fn_tableRelease(){
	
	$button = $("#btn_xAxis");
	
	$button.data("status", "0");
	$button.attr("alt", xAxisFix).attr("title", xAxisFix).text(xAxisFix);
	
	$("#copyTableDiv, #copyTableHeaderDiv").remove();
	
	g_leftThWidth = 0;//열고정 해제시 좌측 타이틀 폭 초기화
}

//빈셀 칼럼 제거
function fn_removeCol(table){
	if( $(table).find("thead tr:last th[coldelyn = 'Y']").length > 0 ){
		//fn_headerUnmerge(table);//삭제전 타이틀 병합 해제(사용안함. java에서 처리함)
		fn_removeNullCol(table);//빈셀삭제		
	}
	
	fn_headerMerge(table);//삭제후 타이틀 병합 재병합
}

//Null 칼럼 삭제 여부체크
function fn_removeColCheck(){

	if($("#htmlGrid #mainTable").find("thead tr:last th[coldelyn = 'Y']").length > 0){					
		//삭제칼럼 찾기
		var delIdxArr = new Array();
		 
		$("#htmlGrid #mainTable").find("thead tr:last th").each(function(tdIndex, th){
			if($(th).attr("coldelyn") == "Y"){							
				delIdxArr.push(tdIndex);
			}			       
		});
		
		$.each(delIdxArr, function(idx, val){
			$("#htmlGrid #mainTable").find("tbody").find("tr").each(function(trIndex, tr){
				if( $.trim( $(tr).find("td").eq(val).find("span.val").text() ) != "-" ){
					$("#htmlGrid #mainTable").find("thead tr:last th").eq(val).removeAttr("coldelyn");	
					$("#ThtmlGrid #mainTableT").find("thead tr:last th").eq(val).removeAttr("coldelyn");		
					return false;//한셀이라도 값 존재시 이후 체크안함
				}
			});
		});				
		
	}

}

//Null 칼럼 삭제
function fn_removeNullCol(table){
	
	if(table.find("thead tr:last th[coldelyn = 'Y']").length > 0){					
		//삭제칼럼 찾기
		var delIdxArr = new Array();
		 
		table.find("thead tr:last th").each(function(tdIndex, th){
			if($(th).attr("coldelyn") == "Y"){							
				//console.log("tdIndex="+tdIndex);
				delIdxArr.push(tdIndex);
			}			       
		});					
		
		delIdxArr.sort(function (a,b){
			return b-a;
		});					
		
		//colgroup 삭제
		$.each(delIdxArr, function(idx, val){
			table.find("colgroup").find("col:eq("+val+")").remove();
		});
		  
		//헤더삭제					
		table.find("thead").find("tr").each(function(trIndex, tr){
			//console.log("trIndex="+trIndex);
			$.each(delIdxArr, function(idx, val){
				//$("#htmlGrid #mainTable").find("thead, tbody").find("tr").find("th,td").length							
				//console.log("tr="+trIndex+"		th="+val+"		th html="+$(tr).find("th").eq(val).html());
				$(tr).find("th").eq(val).remove();							
			});
		});
		
		//바디삭제
		table.find("tbody").find("tr").each(function(trIndex, tr){
			$.each(delIdxArr, function(idx, val){													
				$(tr).find("td").eq(val).remove();							
			});
		});
		
	}	
}

//좌측 타이틀 영역 rowspan 병합해제(사용안함. 분할조회시 java에서 병합생략으로 대신 처리함)
/*function fn_headerUnmerge(table){
	//좌측 틀고정 헤더 병합해제				
	var rowSpanVal = parseInt(table.find("thead tr:eq(0) th.rowHead").attr("rowspan"));
	console.log("rowSpanVal="+rowSpanVal);
	
	if( table.find("thead tr:eq(0) th.rowHead").is('[rowspan]')){
		if(rowSpanVal > 1){						
			//rowspan 셀이라면 unmerge	
			for(var i = 0; i < rowSpanVal-1; i++){						
				table.find("thead tr:eq("+i+") th.rowHead").each(function(thIndex, th){
					
					var $copyTh = $(th).clone();//해당th의 내용복사
					$copyTh.attr("rowspan", "1");//colspan 해제
					$(th).attr("rowspan", "1");//colspan 해제
					var copyHtml = $copyTh.wrap("<div>").parent().html();//colpsan 삭제내용
					//console.log("trIndex="+i+"	thIndex="+thIndex + "	좌측 헤더 복사내용 = "+ copyHtml);
					//제거한  rowspan 수만큼 th생성
													
					table.find("thead tr:eq("+(i+1)+") th").eq(thIndex).before(copyHtml);								
				});
			}
				
		}
	}
		
	//우측 값 헤더 병합해제
	table.find("thead").find("tr").each(function(trIndex, tr){
		$(tr).find("th").not("th.sortRowHead").each(function(thIndex, th){
			
			if($(th).is("[colspan]")){
				var colspanVal = parseInt($(th).attr("colspan")) - 1;
				var $copyTh = $(th).clone();//해당th의 내용복사
				$copyTh.attr("colspan", "1");//colspan 해제
				$(th).attr("colspan", "1");//colspan 해제
				$copyTh.find("span:last").css("width","97px");
				$(th).find("span:last").css("width","97px");
				var copyHtml = $copyTh.wrap("<div>").parent().html();//colpsan 복사할 내용
				//console.log("우측 헤더 복사내용 = "+ copyHtml);
				
				//제거한 colpsan 수만큼 th생성
				for(var i = 0; i < colspanVal; i++){
					$(th).after(copyHtml);
				}
			}
		});
	});
	
}*/

//상단 타이틀 영역 테이블 병합
function fn_headerMerge(table){
	
	//좌측 타이틀 병합
	for(var idx = 0; idx < g_leftHeaderSize; idx++){
		table.rowspan(idx);				    
	}

	//우측 타이틀 병합
	var that = null;
	if($("#assayOriginData").prop("checked") && $("#doAnal").val()=="Y" && $("#analWithCHGRATEChk").prop("checked")){//원자료함께보기 체크, 증감률함께보기 체크시
		
		var lastChild3 = $("#htmlGrid #mainTable").find("thead").find("tr").length - 3;
		table.find("thead").find("tr").not("tr:last, tr:nth-last-child(2)").each(function(trIndex, tr){//마지막2개행 제외
			
			$(tr).find("th").not("th.rowHead, th.sortRowHead").each(function(thIndex, th){
				
				//계층컬럼보기로 추가된 행(소계)이거나 실질적인 최하위레벨(마지막에서 3번째:마지막은 정렬행, 마지막 2번째행은 원대이터 행) tr일 경우 [원데이터] 추가로 인하여 홀수 th에서 2칸씩 병합
				if(  ( ($(th).text().trim() == "소계" ) || ( $(th).text().trim() == "Sub Summary" ) || (trIndex == lastChild3) ) ){
					
					if (($(th).text().trim() == $(that).text().trim())){ //
						colspan = $(that).attr("colSpan") || 1; 
						colspan = Number(colspan)+1; 
						$(that).attr("colSpan",colspan); 
						$(that).find("span:last").css("width", (colspan * 97)+"px"); 
						$(th).hide(); 
					} else {
						that = th; 
					}
					
				}else{
				//같은 셀만큼 모두 병합	
					if ( ($(th).text().trim() == $(that).text().trim()) ){
						colspan = $(that).attr("colSpan") || 1; 
						colspan = Number(colspan)+1; 
						$(that).attr("colSpan",colspan); 
						$(that).find("span:last").css("width", (colspan * 97)+"px"); 
						$(th).hide(); 
					} else {
						that = th; 
					} 
				}
				that = (that == null) ? th : that;					

			});
		});
		
	}else if($("#assayOriginData").prop("checked") && $("#doAnal").val()=="Y"){//원자료함께보기 체크시
		
		var lastChild3 = $("#htmlGrid #mainTable").find("thead").find("tr").length - 3;
		table.find("thead").find("tr").not("tr:last, tr:nth-last-child(2)").each(function(trIndex, tr){//마지막2개행 제외
			$(tr).find("th").not("th.rowHead, th.sortRowHead").each(function(thIndex, th){
				
				//계층컬럼보기로 추가된 행(소계)이거나 실질적인 최하위레벨(마지막에서 3번째:마지막은 정렬행, 마지막 2번째행은 원대이터 행) tr일 경우 [원데이터] 추가로 인하여 홀수 th에서 2칸씩 병합
				if(  ( ($(th).text().trim() == "소계" ) || ( $(th).text().trim() == "Sub Summary" ) || (trIndex == lastChild3) ) ){

					if (($(th).text().trim() == $(that).text().trim()) && (thIndex%2 == 1) ){ //홀수일때 병합
						colspan = $(that).attr("colSpan") || 1; 
						colspan = Number(colspan)+1;
						$(that).attr("colSpan",colspan); 
						$(that).find("span:last").css("width", (colspan * 97)+"px"); 
						$(th).hide(); 
					} else {
						that = th; 
					}
				}else{
				//같은 셀만큼 모두 병합	
					if ( ($(th).text().trim() == $(that).text().trim()) ){
						colspan = $(that).attr("colSpan") || 1; 
						colspan = Number(colspan)+1; 
						$(that).attr("colSpan",colspan); 
						$(that).find("span:last").css("width", (colspan * 97)+"px"); 
						$(th).hide(); 
					} else {
						that = th; 
					} 
				}
				that = (that == null) ? th : that;					

			});
		});
		
	}else if($("#analWithCHGRATEChk").prop("checked") && $("#doAnal").val()=="Y"){//원자료함께보기 체크시
		
		var lastChild3 = $("#htmlGrid #mainTable").find("thead").find("tr").length - 3;
		table.find("thead").find("tr").not("tr:last, tr:nth-last-child(2)").each(function(trIndex, tr){//마지막2개행 제외
			$(tr).find("th").not("th.rowHead, th.sortRowHead").each(function(thIndex, th){
				
				//계층컬럼보기로 추가된 행(소계)이거나 실질적인 최하위레벨(마지막에서 3번째:마지막은 정렬행, 마지막 2번째행은 원대이터 행) tr일 경우 [원데이터] 추가로 인하여 홀수 th에서 2칸씩 병합
				if(  ( ($(th).text().trim() == "소계" ) || ( $(th).text().trim() == "Sub Summary" ) || (trIndex == lastChild3) ) ){

					if (($(th).text().trim() == $(that).text().trim()) && (thIndex%2 == 1) ){ //홀수일때 병합
						colspan = $(that).attr("colSpan") || 1; 
						colspan = Number(colspan)+1;
						$(that).attr("colSpan",colspan); 
						$(that).find("span:last").css("width", (colspan * 97)+"px"); 
						$(th).hide(); 
					} else {
						that = th; 
					}
				}else{
				//같은 셀만큼 모두 병합	
					if ( ($(th).text().trim() == $(that).text().trim()) ){
						colspan = $(that).attr("colSpan") || 1; 
						colspan = Number(colspan)+1; 
						$(that).attr("colSpan",colspan); 
						$(that).find("span:last").css("width", (colspan * 97)+"px"); 
						$(th).hide(); 
					} else {
						that = th; 
					} 
				}
				that = (that == null) ? th : that;					

			});
		});
	}else{//원자료함께보기 체크 해제시(일반)
		
		table.find("thead").find("tr").not("tr:last, tr:nth-last-child(2)").each(function(trIndex, tr){
			$(tr).find("th").not("th.rowHead, th.sortRowHead").each(function(thIndex, th){
				//table.colspan(trIndex);//변경전(속도느림)
				
				if ( ( $(th).text().trim() == $(that).text().trim() ) && ( ($(th).text().trim() != "소계") && ($(th).text().trim() != "Sub Summary") )){					
					colspan = $(that).attr("colSpan") || 1; 
					colspan = Number(colspan)+1;
					$(that).attr("colSpan",colspan); 
					$(that).find("span:last").css("width", (colspan * 97)+"px"); 
					$(th).hide(); 
				} else {
					that = th; 
				} 
				that = (that == null) ? th : that;

			});
		});
		
	}	

}
	
$.fn.rowspan = function(colIdx, isStats) { 
	return this.each(function(){ 
		var that; 
		$('thead tr', this).each(function(row) { 
			$('th:eq('+colIdx+')', this).filter(':visible').each(function(col) { 
			if ($(this).html() == $(that).html() && (!isStats || isStats && $(this).prev().html() == $(that).prev().html() ) ) { 
				rowspan = $(that).attr("rowspan") || 1; 
				rowspan = Number(rowspan)+1; 
				$(that).attr("rowspan",rowspan); 
				$(this).hide();
			} else { 
				that = this; 
			} 
			that = (that == null) ? this : that; 
			}); 
		}); 
	}); 
};

//가로스크롤 존재여부
$.fn.hasHorScrollBar = function(){
	return this.get(0) ? this.get(0).scrollWidth > this.innerWidth() : false;
};

//세로스크롤 존재여부
$.fn.hasVerScrollBar = function(){		
	return this.get(0) ? this.get(0).scrollHeight > this.innerHeight() : false;
};

//사용안함
/*$.fn.colspan = function(rowIdx) { 
	return this.each(function(){ 
		var that; 
		$('tr', this).filter(":eq("+rowIdx+")").each(function(row) { 
			$(this).find('th').filter(':visible').each(function(col) {
			if ($(this).text() == $(that).text()) {
				colspan = $(that).attr("colSpan") || 1; 
				colspan = Number(colspan)+1; 
				$(that).attr("colSpan",colspan); 
				$(that).find("span:last").css("width", (colspan * 97)+"px"); 
				$(this).hide(); 
			} else {
				that = this; 
			} 
				that = (that == null) ? this : that; 
			}); 
		}); 
	}); 
}*/

function cf_getContextPath(){
	var offset = location.href.indexOf(location.host) + location.host.length;
	var ctxPath = location.href.substring(offset, location.href.indexOf('/', offset + 1));
	
	return ctxPath;
}

var outerData;

function fn_getChartData(){
	$.ajax({
		  dataType : 'json'
		, type : 'POST'
		, url : cf_getContextPath()+"/getChartData.do"
		, dataType : "json"
		, data : $("#ParamInfo").serialize()
		, async : false
		, success : function(response,status){
			outerData = response;
			g_chart    = response.result[0];
			g_chartLableArr = g_chart.lable;			/* 챠트 표두 list */
			g_chartDataArr  = g_chart.data;				/* 챠트 표측title 및 데이터 list */
			g_chartMsg		= g_chart.msg;				/* 챠트 조합 생성 여부 */
			g_remarkH 		= g_chart.remarkH;
			g_remarkB 		= g_chart.remarkB;
			
		}
		, error : function(error){
			//fn_progressBar('hide');					
			alert( "에러가 발생했습니다!" );
		}
	});
	
}

//시점 tab 체크표시
function fn_setTimeCheckIcon(time) {
	if($.ui.fancytree.getTree("#timeList" + time).getSelectedNodes().length > 0) {
		$("#ico_chk_"+time).css("display", "");
	} else {
		$("#ico_chk_"+time).css("display", "none");
	}
}

//전체선택 체크박스 초기 설정
function fn_setReleaseCheck(treeId) {
	if($.ui.fancytree.getTree("#" + treeId).getSelectedNodes().length ==  $.ui.fancytree.getTree("#" + treeId).getRootNode().children.length) {
		$("#treeCheckAll" + treeId.replace("fancytree_", "").replace("timeList", "")).prop("checked", true);
	} else {
		$("#treeCheckAll" + treeId.replace("fancytree_", "").replace("timeList", "")).prop("checked", false);
	}
}

//Tree 세팅
function fn_setFancyTree(source, treeId, searchId, multiSelectId) {
	var icon = true;
	if(treeId.indexOf("0") > -1 || treeId.indexOf("timeList") > -1 || treeId.indexOf("timePopList") > -1) icon = false;
	
	$("#" + treeId).fancytree({
		extensions: ["multi","filter"],
		aria : false,
		source : source,
		checkbox: true,
		selectMode: 2,
		icon : icon,
		multi : {
			
		},
		click: function(event, data) {
			if(data.targetType == undefined) {
				event.preventDefault();
				return;
			}
			
			if(data.targetType == "checkbox" || data.targetType == "prefix") {
				data.targetType="title";
			}
			
			if($.ui.fancytree.getTree("#" + treeId).getSelectedNodes().length == 0 && data.originalEvent.shiftKey == true) {
				data.tree.activeNode = data.node;
			}
			
			if((data.targetType == "title" || data.targetType == "icon") && data.originalEvent.shiftKey == false) {
				if($.ui.fancytree.getTree("#" + treeId).getSelectedNodes().length != 0) {
					data.originalEvent.ctrlKey = true;
				}
			}
			
			if(data.node.selected == true) {
				data.node._lastSelectIntent = false;
			}
			
			if(data.originalEvent.ctrlKey == true) {
				$.ui.fancytree.getTree("#" + treeId).getNodeByKey(data.node.key).setActive();
			}
		},
		select: function(event, data) {
			//test 시점팝업 체크여부 확인
			if(treeId.indexOf("timePopList") > -1){
				var idx = treeId.length-1;
				var result = treeId.substr(idx,1);
				fn_chk_prd(result);
			}
			
			if(treeId.indexOf("timeList") > -1) {
				fn_setTimeCheckIcon(treeId.replace("timeList", ""));
				
				var headCnt = 0;
				for(var i=0; i<g_result.length; i++) {
					if($.ui.fancytree.getTree("#timeList" + g_result[i]).getSelectedNodes().length > 0)  headCnt++;
				}
				
				if(headCnt == 1){
					for(var i=0; i<g_result.length; i++) {									
						if($.ui.fancytree.getTree("#timeList" + g_result[i]).getSelectedNodes().length > 0){
							 g_headType = g_result[i];
						}
					}
					
					if(fn_timeCheck() && form.funcPrdSe.value != g_headType) fn_getInitAssayInfo(g_dataOpt);
				}
				
				fn_setTableTypeOption();
				fn_setAssayPopupDisplay();
			}
			
			if($("#" + treeId + "CheckOption").val() != "none") fn_getLowLevel(treeId, multiSelectId, data.node, data.node.selected, $("#" + treeId + "CheckOption").val());
			fn_setInitSelectEvent(treeId, multiSelectId, data.node);
		},
		filter: {
			autoApply : true,
			autoExpand : true,
			counter : true,
			fuzzy : false,
			hideExpandedCounter : true,
			hideExpanders : true,
			highlight : true,
			leavesOnly : false,
			nodata : false,
			mode : "hide"
		}
	});
	
	if(treeId.indexOf("0") <= -1 && treeId.indexOf("time") <= -1) $("#" + treeId + " .fancytree-container").addClass("fancytree-connectors");
	fn_setReleaseCheck(treeId);
	
	if(multiSelectId != null) {
		$("#" + multiSelectId).multiselect({
			onOptionClick: function(element, option) {
				fn_changeTreeCheckVal(treeId, option.value, option.checked);
				
				var checkAllLevel = false;
				
				$.ui.fancytree.getTree("#" + treeId).getRootNode().visit(function(node) {
					if(node.selected == true) checkAllLevel = true;
				});
				fn_changeCheckAllBtnText(checkAllLevel, treeId);
			},
			texts: {
				placeholder: selectLevelText
			},
			onControlClose: function(element) {
				$("#" + multiSelectId + "_screen").css("display", "none");
			},
		});
		
		fn_changeMultiselectVal(multiSelectId, treeId);
	}else {
		if($.ui.fancytree.getTree("#" + treeId).getSelectedNodes().length > 0) {
			fn_changeCheckAllBtnText(true, treeId);
		}
	}
}

//multiselect 클릭 시 tree 가리는 DIV 호출
function fn_showTreeScreen(treeCount) {
	if($("#ui-accordion-tabAccordion-panel-" + treeCount + " .ms-options-wrap").attr("class").indexOf("ms-active") > -1) {
		$("#multiSelect_" + treeCount + "_screen").css("display", "block");
	}
}

//tree 검색 버튼
function fn_keywordTreeBtn(treeId, searchId) {
	$.ui.fancytree.getTree("#" + treeId).filterNodes.call($.ui.fancytree.getTree("#" + treeId), $("#" + searchId).val(), "dimm");
	
	//1렙 노드만 있는 트리인지 확인 후 전체선택 텍스트 및 체크 수정
	if($("#multiSelect_" + treeId.replace("fancytree_", "")).length == 0) {
		treeFilter[treeId] = $("#" + searchId).val() == "" ? false : true;
		
		if(!treeFilter[treeId]) {
			fn_setReleaseCheck(treeId);
		}
		
		fn_setFilterTreeCheck(treeId);
	}
}

//tree 하위레벨 확인 재귀 function
function fn_getLowLevel(treeId, multiSelectId, node, selected, option) {
	var node_tmp;
	
	if(node.children != null) {
		for(var i=0; i<node.children.length; i++) {
			node_tmp = node.children[i];
			
			if(node_tmp.folder) {
				fn_getLowLevel(treeId, multiSelectId, node_tmp, selected, option);
				if(option == "allLowLevel") node_tmp.setSelected(selected, {noEvents : true});
			} else {
				node_tmp.setSelected(selected, {noEvents : true});
			}
		}
	} else {
		node.setSelected(selected, {noEvents : true});
	}
}

//tree Init Select Event
function fn_setInitSelectEvent(treeId, multiSelectId, node) {
	fn_syncGlobalCountVar(treeId);
	fn_changeMultiselectVal(multiSelectId, treeId);
}

//tree expand or collapse
function fn_expandAllNodes(treeId, obj) {
	var expand = true;
	if($(obj).attr("class") == "expandBtn") expand = true;
	else expand = false;
	
	$.ui.fancytree.getTree("#" + treeId).expandAll(expand);
	
	if(!expand) {
		$(obj).attr("class", "expandBtn");
		$(obj).text(expandText);
	} else {
		$(obj).attr("class", "collapseBtn");
		$(obj).text(collapseText);
	}
}

//시점 tree reload
function fn_changeSource(treeId, source) {
	$.ui.fancytree.getTree("#" + treeId).reload(source);
	
	fn_selectNodes(treeId, "1", true);
}

//multiselect check박스로 수정 시 tree 전체선택되게
function fn_changeTreeCheckVal(treeId, value, checked) {
	var selectMode = $.ui.fancytree.getTree("#" + treeId).options.selectMode;
	
	if(selectMode == 3) {
		if(confirm("하위레벨도 같이 선택되었습니다.")) {
			fn_selectNodes(treeId, value, checked);
		}
	} else {
		fn_selectNodes(treeId, value, checked);
	}
}

function fn_selectNodes(treeId, value, checked) {
	$.ui.fancytree.getTree("#" + treeId).getRootNode().visit(function(node) {
		if(value == node.getLevel()+"") {
			node.setSelected(checked, {noEvents : true});
			if($("#" + treeId + "CheckOption").val() != "none") fn_getLowLevel(treeId, "multiSelect_" + treeId.replace("fancytree_",""), node, node.selected, $("#" + treeId + "CheckOption").val());
		}
	});
	
	fn_changeMultiselectVal("multiSelect_" + treeId.replace("fancytree_",""), treeId);
	checkMultiSelect = true;
	fn_setDefaultClassArr(treeId);
	
}

//filter된 트리인지 환인 후 전체선택 text 수정
function fn_setFilterTreeCheck(treeId) {
	//선택 or 전체선택 택스트 수정
	if(treeFilter[treeId]) fn_changeCheckText(fn_checkFilterSelected(treeId), treeId);
	else {
		var checkAllLevel = false;
		
		$.ui.fancytree.getTree("#" + treeId).getRootNode().visit(function(node) {
			if(node.selected == true) checkAllLevel = true;
		}); 
		
		fn_changeCheckAllBtnText(checkAllLevel, treeId);
		fn_setReleaseCheck(treeId);
	}
}

//filter노드가 전체 선택되어있는지 확인
function fn_checkFilterSelected(treeId) {
	var filterCheck = true;
	
	if($("#" + treeId + " ul li .fancytree-match").length == 0) return filterCheck;
	
	$("#" + treeId + " ul li .fancytree-match").each(function(index) {
		if(!$(this).hasClass("fancytree-selected")) filterCheck = false;
	});
	
	return filterCheck;
}

//전체선택, 전체해제 버튼
function fn_checkAllLevel(multiSelectId, treeId) {


	var checked = true;
	
	if(treeFilter[treeId] && multiSelectId == "none") {
		
		//1레벨 노드만 있는 트리의 경우 filter가 되어있으면 filter된 노드만 전체선택
		var hasSelectedNode = false;
	
		for(var i=0; i<$("#" + treeId + " ul li .fancytree-match").length; i++) {
			var filterNode = $("#" + treeId + " ul li .fancytree-match")[i];
			
			if($(filterNode).hasClass("fancytree-selected")) {
				hasSelectedNode = true;
				break;
			}
		}
	
		$.ui.fancytree.getTree("#" + treeId).getRootNode().visit(function(node) {
			for(var i=0; i<$("#" + treeId + " ul li .fancytree-match").length; i++) {
				var filterNode = $("#" + treeId + " ul li .fancytree-match")[i];
				
				if($(filterNode).text() == node.title) {
					node.setSelected(!hasSelectedNode);
					break;
				}
			}
		});
		
		fn_setFilterTreeCheck(treeId);
	} else {
	
		if(treeId.indexOf("timePopList") > -1){
			var idx = treeId.length-1;
			var result = treeId.substr(idx,1);
			switch (result) {
			case "M":
				$("#samePrdseYear_"+result).val("").prop("selected",true);
					$("#samePrdse_"+result).val("").prop("selected",true);
				break;
			case "Q":
				$("#samePrdseYear_"+result).val("").prop("selected",true);
					$("#samePrdse_"+result).val("").prop("selected",true);
				break;
			case "H":
				$("#samePrdseYear_"+result).val("").prop("selected",true);
					$("#samePrdse_"+result).val("").prop("selected",true);
				break;
			case "Y":
				$("#samePrdseYear_"+result).val("").prop("selected",true);
				break;
			}
			
		}
		
		//항목, 1레벨분류, 시점은 multiselectid가 none이므로 이에따른 전체선택 체크박스 값에 따라 트리 동작
		if(multiSelectId == "none") {
			
			if($("#treeCheckAll" + treeId.replace("fancytree_", "").replace("timeList", "")).prop("checked")) {
				$.ui.fancytree.getTree("#" + treeId).getRootNode().visit(function(node) {
					node.setSelected(true, {noEvents : true});
				});
			} else {
				$.ui.fancytree.getTree("#" + treeId).getRootNode().visit(function(node) {
					node.setSelected(false, {noEvents : true});
				});
			}
			
			if(treeId.indexOf("timeList") > -1) {
				fn_setTimeCheckIcon(treeId.replace("timeList", ""));
				
				fn_setTableTypeOption();
				fn_setAssayPopupDisplay();
				if(fn_timeCheck()) fn_getInitAssayInfo(g_dataOpt);
			}
		} else {
			
			if($.ui.fancytree.getTree("#" + treeId).getSelectedNodes().length > 0) {
				
				checked = false;
			} else {
				checked = true;
			}
			
			if(checked) {
				
				$.ui.fancytree.getTree("#" + treeId).getRootNode().visit(function(node) {
				
					node.setSelected(true, {noEvents : true});
				});
			} else {
				$.ui.fancytree.getTree("#" + treeId).getRootNode().visit(function(node) {

					node.setSelected(false, {noEvents : true});
				});
			}
			fn_changeMultiselectVal(multiSelectId, treeId);
		}
	}

	if(treeId.indexOf("0") > -1) {
		g_itmCnt = $.ui.fancytree.getTree("#fancytree_0").getSelectedNodes().length;
		
		fn_countView(g_itmCnt,g_classCnt,g_timeCnt,g_classViewCntStr);
	} else if(treeId.indexOf("fancytree") > -1) {
		
		fn_setDefaultClassArr(treeId);
	} else if(treeId.indexOf("timeList") > -1) {
	
		g_timeCnt = 0;
		for(var i=0; i<timeTreeList.length; i++) {
			g_timeCnt += $.ui.fancytree.getTree("#timeList" + timeTreeList[i]).getSelectedNodes().length;
		}
		fn_countView(g_itmCnt,g_classCnt,g_timeCnt,g_classViewCntStr);
	} else if(treeId.indexOf("timePopList") > -1) {
		g_timePopCnt = 0;
		for(var i=0; i<timeTreeList.length; i++) {
			g_timePopCnt += $.ui.fancytree.getTree("#timePopList" + timeTreeList[i]).getSelectedNodes().length;
		}
		fn_countView(g_itmCnt,g_classCnt,g_timePopCnt,g_classViewCntStr);

		fn_chk_prd(result);
	}
	
	fn_setPivotColChk();
}

//조회설정 단어검색 keyup - backspace시 input 비우기
function fn_searchKeywordKeyup(obj, treeCount) {
	if(window.event.keyCode == 8) {
//		$(obj).val("");
	} else if(window.event.keyCode == 13) fn_keywordTreeBtn('fancytree_' + treeCount, 'searchTree_' + treeCount);
	
	if($(obj).val() != "") {
		$("#emptyKeyword_" + treeCount).css("display", "flex");
	} else {
		$("#emptyKeyword_" + treeCount).css("display", "none");
		fn_emptySearchKeyword(treeCount);
	}
}

function fn_emptySearchKeyword(treeCount) {
	$("#searchTree_" + treeCount).val("");
	$("#emptyKeyword_" + treeCount).css("display", "none");
	fn_keywordTreeBtn('fancytree_' + treeCount, 'searchTree_' + treeCount);
}

function fn_keyDetailPopSelect(value, tabSn){
	if(window.event.keyCode == 13){
		fn_detailPopSelect(value, tabSn);
	}
}
//시점 TreePopup 변경
function fn_detailPopSelect(value, tabSn) {	
	var tabStatus = $(this).attr("class");
	
	$("#detailTab li:eq("+g_defaultTabSn+")").attr("class","tab_off");
	$("#detailTab li:eq("+tabSn+")").attr("class","tab_on");
	$("#timeLeft_"+g_defaultTabSn).css("display","none");
	$("#timeLeft_"+tabSn).css("display","block");
	$("#timeAlignDiv_"+g_defaultTabSn).css("display","none");
	$("#timeAlignDiv_"+tabSn).css("display","block");
	if(g_dataOpt == "en" || g_dataOpt == "cden"){
		$("#timeAlignDiv_"+tabSn).css("width","200px");		
		$("#timeAddSet_"+tabSn).css("width","300px");
		$("#listBox_"+tabSn).css("width","230px");
		$("#timeAddMsgSet_"+tabSn).css("width","300px");
	}else{
		$("#timeAlignDiv_"+tabSn).css("width","146px");
		$("#timeAddSet_"+tabSn).css("width","168px");
		$("#listBox_"+tabSn).css("width","172px");
		$("#timeAddMsgSet_"+tabSn).css("width","168px");
	}
	$("#timeAddSet_"+g_defaultTabSn).css("display","none");
	$("#timeAddSet_"+tabSn).css("display","block");
	$("#timeAddSet_"+tabSn).css("height","30px");
	$("#timeAddSet_"+tabSn).css("float","right");

	
	$(".timePopList").css("display", "none");
	$("#timePopListDiv"+value).css("display", "block");

	g_defaultTabSn = tabSn;
	g_defaultTabType = value;
	
	if($("#tableType").val() == "perYear"){
		fn_setTableTypeOption();
	}
}

//시점 Tree 변경
function fn_detailSelect(selectValue, obj) {
	$(".treeTimeTabSelect").attr("class", "treeTimeTab");
	$(obj).addClass("treeTimeTabSelect");
	$(".timeList").css("display", "none");
//	$(".timeListCheckBox").css("display", "none");
	$("#timeListDiv"+selectValue).css("display", "block");
//	$("#timeListCheckBox"+selectValue).css("display", "flex");
	
	if($("#tableType").val() == "perYear"){
		fn_setTableTypeOption();
		
	}
}


//시점버튼 조회설정 변경시 변경 이벤트
function fn_time_pop_list_set(searchType){
	var tree = $.ui.fancytree.getTree("#timePopList" + searchType);
	tree.visit(function(node){							
		node.setSelected(false, {noEvents : true});
	});
	

	tree.visit(function(node){	
		leftValue = fn_generatePrdDe(node.data.prdDe,searchType);
		var selectNodes = $.ui.fancytree.getTree("#timeList" + searchType).getSelectedNodes();
		for(var j=0; j<selectNodes.length;j++){
			var prdDe = fn_generatePrdDe(selectNodes[j].data.prdDe,searchType);
			if(prdDe == leftValue){
				node.setSelected(true, {noEvents : true});
			}
		}
	});
}

//항목, 분류, 시점 전역 변수 Tree 체크값으로 수정
function fn_syncGlobalCountVar(treeId) {
	if(treeId.indexOf("0") > -1) {
		g_itmCnt = $.ui.fancytree.getTree("#fancytree_0").getSelectedNodes().length;
		fn_countView(g_itmCnt,g_classCnt,g_timeCnt,g_classViewCntStr);
	} else if(treeId.indexOf("fancytree") > -1) {
		fn_setDefaultClassArr(treeId);
	} else if(treeId.indexOf("timeList") > -1) {
		g_timeCnt = 0;
		var treeNm = "";
		if(treeId.indexOf("timeList") > -1){
			treeNm = "timeList";
		}
		for(var i=0; i<timeTreeList.length; i++) {
			g_timeCnt += $.ui.fancytree.getTree("#"+ treeNm + timeTreeList[i]).getSelectedNodes().length;
		}
		
		fn_countView(g_itmCnt,g_classCnt,g_timeCnt,g_classViewCntStr);
	}else if(treeId.indexOf("timePopList") > -1){
		g_timePopCnt = 0;
		var treeNm = "";
		if(treeId.indexOf("timePopList") > -1){
			treeNm = "timePopList";
		}
		for(var i=0; i<timeTreeList.length; i++) {
			g_timePopCnt += $.ui.fancytree.getTree("#"+ treeNm + timeTreeList[i]).getSelectedNodes().length;
		}
		
		fn_countView(g_itmCnt,g_classCnt,g_timePopCnt,g_classViewCntStr);
	}
	
	fn_setPivotColChk();
}

//시점 선택값 확인 후 분석 종류 가져오기
function fn_getInitAssayInfo(viewMode) {
	form.funcPrdSe.value = g_headType;
	
	if($("#analyzable").val() == "true") {
		//$("#settLoading").css("display", "flex");
		$("#assayInfoSet").empty();
		
		$.ajax({
			type : 'POST',
			url : cf_getContextPath()+"/assayInfo.do",
			dataType : "text",
			data : $("#ParamInfo").serialize(),
			success : function(response,status){
				$("#assayInfoSet").append(response);
				if($("select[name='assayLeft'] option[value=CHG]").length == 0 || $("select[name='assayLeft'] option[value=CHG_RATE]").length == 0) {
					if($("select[name='assayLeft'] option[value=CHG]").length > 0) $("#assayPopupBtn").text(g_analChangeText);
					if($("select[name='assayLeft'] option[value=CHG_RATE]").length > 0) $("#assayPopupBtn").text(g_analPercentChangeText);
				}
				
				$("#assayPopupBtn").css("display", "");
				
				if($("#doAnal").val() == "Y") {
					fn_setAssayBtnDisplay("cancel");
				} else {
					fn_setAssayBtnDisplay("assay");
				}
			},
			error : function(error){
			}
		});
	}
}

//좌상단 시점 버튼 display 유무
function fn_setAssayPopupDisplay() {
	if(fn_timeCheck()) {
		if(g_assayYn != "N"){
			if(g_analyzable == "true"){
				if(g_multiplication <= g_maxCell){
					$("#assayInfoSet").css("display", "block");
					if($("#doAnal").val() == "Y") $("#assayCancelPopupBtn").css("display", "");
					else if($("select[name='assayLeft'] option[value=CHG]").length > 0)$("#assayPopupBtn").css("display", "");
				}
			}
		}
	} else {
		$("#assayInfoSet").css("display", "none");
		$("#assayCancelPopupBtn").css("display", "none");
		$("#assayPopupBtn").css("display", "none");
		//$("select[name=assayLeft] option[value=none]").prop("selected", true);
	}
}

//시점 옆 분석버튼 클릭 시 팝업 호출
function fn_assayPopupSet() {
	if($(".assayPopupBox").css("display") == "none") {
		$sett_box = $(".sett_box");
		$search_sett = $(".search_sett");
		
	    if($sett_box.css('display') != "none"){
	    	if(fn_checkTreeReleaseAll()) {
	    		$sett_box.hide();        	
	        	$search_sett.removeClass("search_sett_show").addClass("search_sett_hide").css("left", "");
	        	    	 
	    		$(".search_sett").css("right", "5px");
	    	} else {
	    		return;
	    	}
	    }
	    
		$(".assayPopupBox").css("min-width", parseInt($("#assayPopupBtn").css("width"), 10)-2);
		$(".assayPopupBox").css("left", $("#assayPopupBtn").offset().left);
		$(".assayPopupBox").css("top", $("#assayPopupBtn").offset().top+23);
		$(".assayPopupBox").css("display", "block");
	} else {
		$(".assayPopupBox").css("display", "none");
	}
	
	if($("#pop_timeSet").css("display") != "none"){
		g_timePopType=false;
		$("#pop_timeSet").hide();
	}
	$("#btn_1").focus();
}

//통계표 시점 옆 분석 assay key event
function fn_keyAssayList(assayInfo){
	if(window.event.keyCode == 13){
		fn_clickAssayList(assayInfo);
	}
}

//통계표 시점 옆 분석 assay popup click
function fn_clickAssayList(assayInfo) {
	fn_assayPopupSet();
	
	var assayLeftInfo = "CHG";
	
	if($("select[name='assayLeft'] option[value=CHG]").length == 0 || $("select[name='assayLeft'] option[value=CHG_RATE]").length == 0) {
		if($("select[name='assayLeft'] option[value=CHG]").length > 0) assayLeftInfo = "CHG";
		if($("select[name='assayLeft'] option[value=CHG_RATE]").length > 0) assayLeftInfo = "CHG_RATE";
		$("#analWithCHGRATEChk").prop("checked", false);
	} else {
		assayLeftInfo = "CHG";
		$("#analWithCHGRATEChk").prop("checked", true);
	}
	
	if(assayLeftInfo != "" && assayInfo != "") {
		$("#assayOriginData").prop("checked", true);
		
		$("select[name=assayLeft] option[value=" + assayLeftInfo + "]").prop("selected", true);
		$("select[name=assayRight] option[value=" + assayInfo + "]").prop("selected", true);
		fn_analTypeTrigger($("select[name='assayLeft']"));
		fn_analCmprTrigger($("select[name='assayRight']"));
		
		if(fn_timeCheck()) {
			var bl_assay = fn_assayStart(true);
			if(bl_assay == true){
				return;
			}
			if($("#assayInfoSet").css("display") != "none"){
				if($("select[name=assayLeft]").val() == "none" && $("select[name=assayRight]").val() == "none"){
					fn_assayCanCel();
				}
			}
			
			//view_sub_kind 컬럼에 쌓을지 체크, jquery로 간단하게 처리
			var logText = "";
			
			if($("#isChangedTableType").val() == "Y"){
				logText += "A";
			}
			
			var dataOpt = g_dataOpt;
			var dataOpt2 = $("#dataOpt2 option:selected").val();
			if(dataOpt != dataOpt2){
				logText += "B";
			}
			
			if($("#isChangedPeriodCo").val() == "Y"){
				logText += "C";
			}
			
			if($(":checkbox[name='enableLevelExpr']").is(":checked") == true){
				logText += "D";
			}
			
			if($(":checkbox[name='enableParentLevel']").is(":checked") == true){
				logText += "E";
			}
			
			if($(":checkbox[name='enableCellUnit']").is(":checked") == true){
				logText += "F";
			}
			
			if($(":checkbox[name='enableWeight']").is(":checked") == true){
				logText += "G";
			}
			
			if($("#isChangedPrdSort").val() == "Y"){
				logText += "H";
			}
			
			//마지막 체크
			if(logText.length > 0){
				form.useAddFuncLog.value = "1_" + logText;
			}
			
			fn_searchTree(true);
		}
	}
}

//시점 다중 선택 확인
function fn_timeCheck() {
	var timeCheck = true;
	var timeZeroChk = false;
	var totalNodeCnt = 0;
	
	if(g_multiplication > 20000) return false;
	
	for(var i=0; i<timeTreeList.length; i++) {
		var selectedNodes = $.ui.fancytree.getTree("#timeList" + timeTreeList[i]).getSelectedNodes();
		if(selectedNodes.length > 0 ) {
			if(!timeZeroChk) timeZeroChk = true;
			else timeCheck = false;
		}
		
		totalNodeCnt += selectedNodes.length;
	}
	
	if(totalNodeCnt == 0) timeCheck = false;
	
	return timeCheck;
}

//분석 버튼 show or hide
function fn_setAssayBtnDisplay(display) {
	if(display == "assay") {
		$("#assayPopupBtn").css("display", "");
		$("#assayPopupBtn").addClass("class", "off");
		$("#assayCancelPopupBtn").css("display", "none");
		$(".assayCancelBtn").css("display", "none");
	} else if(display == "cancel") {
		$("#assayPopupBtn").css("display", "none");
		$("#assayPopupBtn").addClass("class", "off");
		$("#assayCancelPopupBtn").css("display", "");
		$(".assayCancelBtn").css("display", "");
	} else if(display == "all") {
		$("#assayPopupBtn").css("display", "none");
		$("#assayCancelPopupBtn").css("display", "none");
	}
	
	if($("select[name='assayLeft'] option[value='CHG']").length == 0 && $("select[name='assayLeft'] option[value='CHG_RATE']").length == 0) $("#assayPopupBtn").css("display", "none");
}

function fn_apply(){
	if($("#assayInfoSet").css("display") != "none"){
		if($("select[name=assayLeft]").val() != "none" || $("select[name=assayRight]").val() != "none"){
			var bl_assay = fn_assayStart(true);
			if(bl_assay == true){
				return;
			}
		}
	}
	
	if($("#assayInfoSet").css("display") != "none"){
		if($("#assayCancelBtn").css("display") != "none"){
			if($("select[name=assayLeft]").val() == "none" && $("select[name=assayRight]").val() == "none"){
				fn_assayCanCel();
			}
		}
	}
	//view_sub_kind 컬럼에 쌓을지 체크, jquery로 간단하게 처리
	var logText = "";
	
	if($("#isChangedTableType").val() == "Y"){
		logText += "A";
	}
	
	var dataOpt = g_dataOpt;
	var dataOpt2 = $("#dataOpt2 option:selected").val();
	if(dataOpt != dataOpt2){
		logText += "B";
	}
	
	if($("#isChangedPeriodCo").val() == "Y"){
		logText += "C";
	}
	
	if($(":checkbox[name='enableLevelExpr']").is(":checked") == true){
		logText += "D";
	}
	
	if($(":checkbox[name='enableParentLevel']").is(":checked") == true){
		logText += "E";
	}
	
	if($(":checkbox[name='enableCellUnit']").is(":checked") == true){
		logText += "F";
	}
	
	if($(":checkbox[name='enableWeight']").is(":checked") == true){
		logText += "G";
	}
	
	if($("#isChangedPrdSort").val() == "Y"){
		logText += "H";
	}
	
	//마지막 체크
	if(logText.length > 0){
		form.useAddFuncLog.value = "1_" + logText;
	}
	
	fn_searchTree(true);
}

function fn_changeTableType(){
	form.isChangedTableType.value = "Y";
}

function fn_changePeriodCo(){
	form.isChangedPeriodCo.value = "Y";
}

function fn_changePrdSort(){
	form.isChangedPrdSort.value = "Y";
}

function controllParentLevel(flag){
	if(flag == 1){
		if($("#enableLevelExpr").is(':checked')){
			$("#enableParentLevel").attr("checked", false);
		}	
	}else{
		if($("#enableParentLevel").is(':checked')){
			$("#enableLevelExpr").attr("checked", false);
		}
	}
}

function fn_changePopPrdSort(){
	form.isChangedPrdSort.value = "Y";
	if($(":radio[name=prdSort]:checked").val() != $(":radio[name=prdSortPop]:checked").val()) $(":radio[name=prdSort]:checked").val($(":radio[name=prdSortPop]:checked").val());
	
}


function fn_changeTreeCheckOption(obj, treeId) {
	if($(obj).val() == "none"){
		$("#" + treeId).fancytree("option", "selectMode", 2);
	} else if($(obj).val() == "allLowLevel") {
		alert(checkAllLowLevelText);
		$("#" + treeId).fancytree("option", "selectMode", 3);
	} else if($(obj).val() == "lowestLevel") {
		alert(checkLowestLevelText);
		$("#" + treeId).fancytree("option", "selectMode", 2);
	}
	
	$.ui.fancytree.getTree("#" + treeId).getRootNode().visit(function(node) {
		node.setSelected(false, {noEvents : true});
	});
}

function fn_selectItemAll(rangeType){
	var itemChkAllCnt = $.ui.fancytree.getTree("#fancytree_0").getSelectedNodes().length;

	g_itmCnt = itemChkAllCnt;
	fn_countView(g_itmCnt,g_classCnt,g_timeCnt,g_classViewCntStr);
}

/************************************************************************
함수명 : fn_enable
설   명 : 주기별 체크박스 선택시 콤보박스 활성화/비활성화
인   자 : type = 주기(D,T,M,B,Q,H,Y,F)
 ************************************************************************/

function fn_enable(type){

	var timeEnableChk = $.ui.fancytree.getTree("#timeList" + type).getSelectedNodes().length > 0 ? true : false;
	
	//주기별 div->바로 밑에 inputBox 선택여부에 따라 콤보박스 및 조회버튼 활성화/비활성화
	//조회버튼/주기별 시점리스트 활성화 비활성화--%>
	if(timeEnableChk == true){
//		$("#time"+type).find('select').removeAttr("disabled");
	}else{
//		$("#time"+type).find('select').attr("disabled",true);
//		$.ui.fancytree.getTree("#timeList" + type).reload([]);
		var tree = $.ui.fancytree.getTree("#timePopList"+type);
		tree.visit(function(node){							
			node.setSelected(false);
		});
//			$("#searchPeriod"+type).children().remove();									리스트정보 지우기
//			$("#divSelectAll"+type).css("display", "none");	조회버튼 비활성화 되면서 해당 주기의 전체선택 안보이게...
	}
	
	fn_syncGlobalCountVar("#timeList" + type);
	fn_analysisChk(g_analyzable);
	
	fn_setTimeCheckIcon(type);
	
	fn_setTableTypeOption();
	fn_setAssayPopupDisplay();
	if(fn_timeCheck() && form.funcPrdSe.value != g_headType) fn_getInitAssayInfo(g_dataOpt);
}

var tmpDataSet ;
var g_minValue = 0;
var g_maxValue = 0;
	
var g_minXValue = 0;
var g_maxXValue = 0;

var changeColor = new Array();
changeColor = new Array();
changeColor[0] = "#f51111";
changeColor[1] = "#3ef700";
changeColor[2] = "#e38484";
changeColor[3] = "#7080ed";
changeColor[4] = "#13f28e";


$(document).ready(function(){
	//fn_settView();
	//$("#chartOptionDiv").hide();
	
	$("#chartOptionDiv").draggable();
	
	
	$("#btnChartBorder").bind("click", function(){
		if(chartInstance.getChartAttribute("showBorder") === undefined || chartInstance.getChartAttribute("showBorder") == "0"){
			chartInstance.setChartAttribute("showBorder", "1");
		}else{
			chartInstance.setChartAttribute("showBorder", "0");
		}
	});

	$("#btnChartTitle").bind("click", function(){ 
		
		var title = $("#chartTitle").val();

		if(title !== undefined && title != ""){
			chartInstance.setChartAttribute("caption", title);
		}
	});

	$("#btnLegend").bind("click", function(){
		var legendPosition = $(this).data("legendPosition");
		
		console.log(legendPosition);

		if(legendPosition == "RIGHT"){
			chartInstance.setChartAttribute("legendPosition", "BOTTOM");			
			$(this).data("legendPosition", "BOTTOM");
		}else{
			chartInstance.setChartAttribute("legendPosition", "RIGHT");			
			$(this).data("legendPosition", "RIGHT");
		}
	});
	
	$("#btnResize").bind("click", function(){
		var width = $("#chartWidth").val();
		var height = $("#chartHeight").val();
		
		if(width !== undefined && width != "" && height !== undefined && height != ""){
			chartInstance.width = width; chartInstance.height = height; chartInstance.render();				
		}
		
	});
	
	$("#btnResizeCancel").bind("click", function(){
		chartInstance.width = "100%"; chartInstance.height = 500; chartInstance.render();
	});
	
	$("#btnGradient1").bind("click", function(){
		if(chartInstance.getChartAttribute("usePlotGradientColor") === undefined || chartInstance.getChartAttribute("usePlotGradientColor") == "0"){
			chartInstance.setChartAttribute("usePlotGradientColor", "1");
		}else{
			chartInstance.setChartAttribute("usePlotGradientColor", "0");				
		}
	});
	
	$("#btnGradient2").bind("click", function(){
		if(chartInstance.getChartAttribute("showAlternateHGridColor") === undefined || chartInstance.getChartAttribute("showAlternateHGridColor") == "0"){
			chartInstance.setChartAttribute("showAlternateHGridColor", "1");
		}else{
			chartInstance.setChartAttribute("showAlternateHGridColor", "0");				
		}
		if(chartInstance.getChartAttribute("showAlternateVGridColor") === undefined || chartInstance.getChartAttribute("showAlternateVGridColor") == "0"){
			chartInstance.setChartAttribute("showAlternateVGridColor", "1");
		}else{
			chartInstance.setChartAttribute("showAlternateVGridColor", "0");				
		}
	});
	
	$("#btnBgColor").bind("click", function(){
		var inputColor = $("#txtBgColor").val();
		chartInstance.setChartAttribute("bgColor", inputColor);
	});
	
	$("#btnValueColor").bind("click", function(){
		
		
		
		tmpDataSet = chartInstance.getJSONData();
		
		$(tmpDataSet.dataset).each(function(index, data){
			$(data.data).each(function(index2, obj){
				obj.color = changeColor[index2];
			});
		});
		
		chartInstance.setJSONData(tmpDataSet);
		chartInstance.setChartAttribute("palettecolors", changeColor.toString());
		chartInstance.render();
		//chartInstance.setChartAttribute("palettecolors", "#f51111, #3ef700, #e38484,#7080ed,#13f28e");
	});
	
	
	 
	$("#btnChangeLegend").bind("click", function(){
		tmpDataSet = chartInstance.getJSONData();
		
		$(tmpDataSet.dataset).each(function(index, data){
			//console.log("before :: " + data.seriesname);
			var inputSeriesname = $("input[name='legendTitle'][sn="+index+"]").val();
			data.seriesname = inputSeriesname;
			//console.log("after :: "+data.seriesname);
		});
		
		chartInstance.setJSONData(tmpDataSet);
		
	});
	
	$("#btnChangeFont").bind("click", function(){
		
		var font = $("#chartFont").val();
		var fontColor = $("#chartFontColor").val();
		var fontSize = $("#chartFontSize").val();
		
		var gubun = $("#gubun").val();
		
		if(gubun == "captionFont"){
			
			chartInstance.setChartAttribute("captionFont", font);
			
			if(fontColor !== undefined && fontColor != ""){
				chartInstance.setChartAttribute("captionFontColor", fontColor);
			}
			
			if(fontSize !== undefined && fontSize != ""){
				chartInstance.setChartAttribute("captionFontSize", fontSize);
			}
			
		}else if(gubun == "baseFont"){
			
			chartInstance.setChartAttribute("baseFont", font);
			
			if(fontColor !== undefined && fontColor != ""){
				chartInstance.setChartAttribute("baseFontColor", fontColor);
			}
			
			if(fontSize !== undefined && fontSize != ""){
				chartInstance.setChartAttribute("baseFontSize", fontSize);
			}
			
		}else{
			
			chartInstance.setChartAttribute("legendItemFont", font);
			
			if(fontColor !== undefined && fontColor != ""){
				chartInstance.setChartAttribute("legendItemFontColor", fontColor);
			}
			
			if(fontSize !== undefined && fontSize != ""){
				chartInstance.setChartAttribute("legendItemFontSize", fontSize);
			}
		}
		
	});
	
	
	var dataset = new Array() ;
	var data = new Object();
	
	
	$("#btnChangeChartType").bind("click", function(){
		var chartType = $("#chartType").val();			
		chartInstance.chartType(chartType);
	});
	
	
	$("#btnRange").bind("click", function(){
		
		tmpDataSet = chartInstance.getJSONData();
		
		var valueFrom 	= parseInt($("#valueFrom").val());
		var valueTo 	= parseInt($("#valueTo").val());
		
			//var valueFrom = 10000000;
			//var valueTo = 50000000;
			var data = new Object();
			var dataset = new Array();


			$(tmpDataSet.dataset).each(function(index, dataIn){
      		  $(dataIn.data).each(function(index2, obj){
                	      		    
      		    var tmpVal = parseInt(obj.value);

      		    if(tmpVal < valueFrom || tmpVal > valueTo){	      		    	
                     console.log(tmpVal);
                     //delete dataIn.data[index2];
                     tmpDataSet.dataset[index].data[index2].value = "0";
      		    }
      		    
      		  });
      		});
      		
			chartInstance.setChartAttribute("yAxisMaxValue", valueTo);
			chartInstance.setChartAttribute("yAxisMinValue", valueFrom);
			chartInstance.setJSONData(tmpDataSet);
			
			
			//이상하네...왜 에러가 납니까요? 
			//var tt = chartInstance.getJSONData();
			//chartInstance.setJSONData(tt);
      		
		
		
		
	});
	
	
	$("#btnRangeX").bind("click", function(){
		
		var insertIndex = new Array();
		
		tmpDataSet = chartInstance.getJSONData();
		
		var valueXFrom 	= parseInt($("#valueXFrom").val());
		var valueXTo 	= parseInt($("#valueXTo").val());
		
		var newCategory = new Array();
		
		$(tmpDataSet.categories[0].category).each(function(index, category){
  		    
			var tmpVal = parseInt(category.label);
			
  		    if(tmpVal >= valueXFrom && tmpVal <= valueXTo){	      		    	
  		    	insertIndex.push(index);
  		    	newCategory.push(category);
  		    }      		    
  		});
	
		console.log("newCategory == "+newCategory);
		console.log("insertIndex == "+insertIndex);
		console.log("newCategory.length == "+newCategory.length);
		console.log("insertIndex.length == "+insertIndex.length);
		
		tmpDataSet.categories[0].category = newCategory;
	
			
		$(tmpDataSet.dataset).each(function(index, dataIn){
				
  			var newData = new Array();
  			
      		$(dataIn.data).each(function(index2, obj){
      			 
  			 
  			  for(var i=0; i < insertIndex.length; i++){
  				  if(insertIndex[i] == index2){
					console.log(i+ "insertIndex == "+insertIndex[i]);
  					newData.push(obj);
  					 //delete tmpDataSet.dataset[index].data[index2];
  				  }
  			  }	
      			  
  			  
  			  console.log("newData.length=========="+newData.length);
  			  
      		  tmpDataSet.dataset[index].data = newData;  
      			  
      	     });
	     });
		
			
		 chartInstance.setJSONData(tmpDataSet);			
	});		

	
	$("#btnLegendDrag").bind("click", function(){
		chartInstance.setChartAttribute("legendAllowDrag", "1");
	});
	
	$("#btnChangeXYName").bind("click", function(){
		
		var yAxisName = $("#yAxisName").val();
		var xAxisName = $("#xAxisName").val();
		
		chartInstance.setChartAttribute("xAxisName", yAxisName);
		chartInstance.setChartAttribute("yAxisName", xAxisName);
	});
	
	//조회설정 열기 keydown이벤트
	$("#ico_querySetting").bind("keydown",function(key){
		
		if (key.keyCode == 13) {	
			fn_settView();
		};
	});
	
	
	//조회조건
	$("#liSetting").bind("keydown",function(key){
		if (key.keyCode == 13) {
			$lis = $("#sett_tab>ul>li");
			$lis.off("keydown");
			$lis.each(function(index, li){	
				$(li).on("keydown", function(e){
					if(e.keyCode === 13){
						var dataTab = $(li).attr("data-tab");
						
						fn_functionControllByItmKd(this, dataTab);
					}
				});					
			});
		};
	});
	
	//조회조건 닫기
	$("#divSchset").bind("keydown",function(key){
		
		if (key.keyCode == 13) {
			
			fn_settView();
		};
	});
	//부가기능
	$("#tab20li").bind("keydown",function(key){
		if (key.keyCode == 13) {
			$lis = $("#sett_tab>ul>li");
			$lis.off("keydown");
			$lis.each(function(index, li){	
				$(li).on("keydown", function(e){
					if(e.keyCode === 13){
						var dataTab = $(li).attr("data-tab");
						
						fn_functionControllByItmKd(this, dataTab);
					}
				});					
			});
		};
	});
});

function fnSetData(dataObj){
	
  $(dataObj.dataset).each(function(index, data){
	  $(data.data).each(function(index2, obj){
	    
	    var tmpVal = parseInt(obj.value);

	    if(g_minValue == 0){
	    	g_minValue = tmpVal;
	    }else{
	      if(g_minValue > tmpVal){
	    	g_minValue = tmpVal;
	      }
	    }

	    

	    if(g_maxValue == 0){
	    	g_maxValue = tmpVal;
	    }else{
	      if(g_maxValue < tmpVal){
	    	g_maxValue = tmpVal;
	      }
	    }
	  });
	})
		
		
	$("#spnMinVal").text(g_minValue);
	$("#spnMaxVal").text(g_maxValue);
		
		
		
		/*
		$(dataObj.categories[0].category).each(function(index, category){
  		    
  		    var tmpVal = parseInt(category.label);

  		    if(g_minXValue == 0){
  		    	g_minXValue = tmpVal;
  		    }else{
  		      if(g_minXValue > tmpVal){
  		    	g_minXValue = tmpVal;
  		      }
  		    }
 		    

  		    if(g_maxXValue == 0){
  		    	g_maxXValue = tmpVal;
  		    }else{
  		      if(g_maxXValue < tmpVal){
  		    	g_maxXValue = tmpVal;
  		      }
  		    }
  		})
  		
  		$("#spnMinXVal").text(g_minXValue);
			$("#spnMaxXVal").text(g_maxXValue);
  		*/
  		
}


function openFullScreenChart() {
	/*var options = "location=yes,toolbar=yes,directories=yes,status=yes,menubar=yes,scrollbars=yes,resizable=yes,width=1024,height=768";
	var newWindow = window.open( "_blank","",options);*/
	var msg = $("#chartMsg").val();
	
	if(g_sortIdx != "-"){
		alert(msg);
		return;
	}

	var myForm = document.ParamInfo;
	var tabNum = top.$("#iframe_rightMenu").contents().find(".stat_tab>ul>li.tab_on").attr("tabindex");//탭번호
	//console.log("tabNum=",tabNum);
	var popwin = window.open("", "newWindow_"+tabNum, "toolbar=no, width=1200,height=800, scrollorbar=no");
	myForm.target = "newWindow_"+tabNum;
	myForm.action = cf_getContextPath()+"/openFullsizeChart.do?g_ChartGubun=" + g_ChartGubun;
	myForm.submit();
	myForm.target = "_self";
}

//시점버튼이벤트
function fn_searchPopPrd(type){
	var cnt = 0;
	for(var i=0; i<timeTreeList.length; i++) {
		var selectNodes = $.ui.fancytree.getTree("#timePopList" +timeTreeList[i]).getSelectedNodes();
		if(selectNodes.length > 0){
			cnt++;
		}
	}
	
	if(cnt == 0){
		alert(g_notSearch);
		return;
	}
	
	if(type == "prd"){
		fn_set_timePop();
		fn_syncGlobalCountVar("timeList");
		var headCnt = 0;
		
		for(var i=0; i<timeTreeList.length; i++) {
			if($.ui.fancytree.getTree("#timeList" + timeTreeList[i]).getSelectedNodes().length > 0){
				headCnt++;
			}
			
			fn_setTimeCheckIcon(timeTreeList[i]);
		}
		
		for(var i=0; i<timeTreeList.length; i++) {
			var selectedNodesCount = $.ui.fancytree.getTree("#timeList" + timeTreeList[i]).getSelectedNodes().length;
			
			if(selectedNodesCount > 0) {
				g_headType = timeTreeList[i];
			}
		}
		
		if(headCnt == 1){
			
			fn_setTableTypeOption();
			fn_setAssayPopupDisplay();
			if(fn_timeCheck() && form.funcPrdSe.value != g_headType) fn_getInitAssayInfo(g_dataOpt);
		}
		fn_searchTree();
		g_timePopType = false;
		$("#pop_timeSet").hide();
	}else{
		if($(type).hasClass("off")) return;
		fn_set_timePop();
		if(g_timePopCnt>0){
			g_timeCnt = g_timePopCnt;
		}
		fn_countView(g_itmCnt,g_classCnt,g_timeCnt,g_classViewCntStr);
		fn_downLarge(type);
		g_timePopType = false;
		$("#pop_timeSet").hide();
	}
	
}
//조회설정 시점 - 시점 버튼 선택 시점 동기화
function fn_set_timePop(){
	g_timePopType = true;
	for(var i=0; i<timeTreeList.length; i++) {
		var selectNodes = $.ui.fancytree.getTree("#timePopList" +timeTreeList[i]).getSelectedNodes();
		if(selectNodes.length > 0){
			var minPrdDe = 0;
			for(var j=0; j<selectNodes.length;j++){
				if(minPrdDe == 0){
					minPrdDe = selectNodes[j].data.prdDe;
				}
				if(minPrdDe > selectNodes[j].data.prdDe){
					minPrdDe = selectNodes[j].data.prdDe;
				}
			}
			
			var maxPrdDe = 0;
			for(var j=0; j<selectNodes.length;j++){
				if(maxPrdDe == 0){
					maxPrdDe = selectNodes[j].data.prdDe;
				}
				if(maxPrdDe < selectNodes[j].data.prdDe){
					maxPrdDe = selectNodes[j].data.prdDe;
				}
			}
			
			
			$("#selectStrtTime"+timeTreeList[i]).val(minPrdDe).prop("selected",true);
			
			if(g_timePopType){

				fn_searchPeriod(timeTreeList[i]);
				var tree = $("#timeList" + timeTreeList[i]).fancytree('getTree');
				tree.visit(function(node){							
					node.setSelected(false, {noEvents : true});
				});
				
				if($("#selectEndTime"+timeTreeList[i]).val() < maxPrdDe){
					$("#selectStrtTime"+timeTreeList[i]).val(minPrdDe).prop("selected",true);
					$("#selectEndTime"+timeTreeList[i]).val(maxPrdDe).prop("selected",true);
					fn_searchPeriod(timeTreeList[i]);
					tree.visit(function(node){							
						node.setSelected(false, {noEvents : true});
					});
				}
				tree.visit(function(node){		

					leftValue = fn_generatePrdDe(node.data.prdDe,timeTreeList[i]);
					for(var j=0; j<selectNodes.length;j++){
						var prdDe = fn_generatePrdDe(selectNodes[j].data.prdDe,timeTreeList[i]);
						if(prdDe == leftValue){
							node.setSelected(true, {noEvents : true});
						}
					}
				});
			}else{
				//팝업이 아닐 경우
				fn_searchPeriod(timeTreeList[i]);
				
			}
		}else{
			//선택된 시점이 없을 경우
			//fn_searchPeriod(timeTreeList[i]);
			$("#treeCheckAll"+timeTreeList[i]).prop('checked', false);
			fn_Headenable(timeTreeList[i]);
			var tree = $("#timeList" + timeTreeList[i]).fancytree('getTree');
			tree.visit(function(node){							
				node.setSelected(false, {noEvents : true});
			});
		}
	}
}
//표두명칭 칼럼 추가
function fn_YAxisCreation(){
	
	var headerRowCnt = $("#htmlGrid #mainTable").find("thead").find("tr").length - 1;//rowspan tr 개수
	if($("#assayOriginData").prop("checked") && $("#doAnal").val()=="Y"){//원자료함께보기 체크시
		headerRowCnt = headerRowCnt - 1;
	}
	
	var html  = "";
	//var ulRightCnt = $("#pop_pivotfunc .pop_content ul#ulRight li").length;//표두 개수
	var ulRightCnt = $("#pop_pivotfunc #ulRight li").length;	//표두 개수
	
	//표두없으면 명칭 칼럼 필요없음
	if(ulRightCnt <= 0){return false;}
	
	if(headerRowCnt > 0 ){
		//colgroup 추가
		if( g_leftHeaderSize == 0 ){
			$("#mainTableT colgroup col:eq("+(g_leftHeaderSize)+")").before("<col class='Selectable1'>");
			$("#mainTable colgroup col:eq("+(g_leftHeaderSize)+")").before("<col class='Selectable1'>");
		}else{
			$("#mainTableT colgroup col:eq("+(g_leftHeaderSize-1)+")").after("<col class='Selectable1'>");
			$("#mainTable colgroup col:eq("+(g_leftHeaderSize-1)+")").after("<col class='Selectable1'>");
		}
		
		//계층컬럼보기 체크시
		if($("#enableLevelExpr").is(':checked')){
			//console.log("-------<계층컬럼보기 체크>--------");
			var befCode = "";
			var curCode = "";
			var title = "";
			var maxLevel = 0;
			var groupIdx = 0;

			for(var i = 0; i < headerRowCnt; i++){
				maxLevel = $("#mainTableT thead tr:eq("+i+") th.colHead-first:first").attr("maxLevel");
				curCode = $("#mainTableT thead tr:eq("+i+") th.colHead-first:first").attr("code");
				
				if(befCode.trim() != curCode.trim()){
					title = $("#pop_pivotfunc ul#ulRight li:eq("+groupIdx+")").text();
					
					//console.log("i = "+i+"	befCode = "+befCode + "		curCode= "+curCode+ "		maxLevel= "+maxLevel+ "		title="+title+ "		groupIdx="+groupIdx);				
					
					for(var j = 0; j < maxLevel; j++){
						if(j == 0){
							html = "<th class='titleHeader rowHead' rowspan='" + maxLevel + "'>"+title+"</th>";
						}else{
							html = "";
						}
						$("#mainTableT thead tr:eq("+i+") th.colHead-first:first").before(html);
						$("#mainTable thead tr:eq("+i+") th.colHead-first:first").before(html);
					}
					groupIdx++;
				}
				
				befCode = curCode;
			}
		}else{
		//계층컬럼보기 체크 해제시(일반경우)
			//console.log("-------<계층컬럼보기 해제>--------");
			for(var i = 0; i < headerRowCnt; i++){
				var title = $("#pop_pivotfunc ul#ulRight li:eq("+i+")").text();
				html = "<th class='titleHeader rowHead'>"+title+"</th>";

				$("#mainTableT thead tr:eq("+i+") th.colHead-first:first").before(html);
				$("#mainTable thead tr:eq("+i+") th.colHead-first:first").before(html);
			}

		}

		//원자료 함께보기 셀추가
		if($("#assayOriginData").prop("checked") && $("#doAnal").val()=="Y"){
			$("#mainTableT thead tr:nth-last-child(2) th.colHead-first:first").before("<th class='titleHeader rowHead'>"+ $("#labelOriginData").val() + "</th>");
			$("#mainTable thead tr:nth-last-child(2) th.colHead-first:first").before("<th class='titleHeader rowHead'>" + $("#labelOriginData").val() + "</th>");
		}

		//정렬 셀 빈칸추가
		$("#mainTableT thead th.sortColHead:first").before("<th class='titleHeader sortRowHead' style='border-bottom:none'>&nbsp;</th>");
		$("#mainTable thead th.sortColHead:first").before("<th class='titleHeader sortRowHead'>&nbsp;</th>");
		//정렬 셀 빈칸추가
		$("#copyMainTableT thead th.sortColHead:first").before("<th class='titleHeader sortRowHead' style='border-bottom:none'>&nbsp;</th>");

		//tbody 셀 빈칸추가
		$("#mainTable tbody tr").each(function(index, tr){
			$(tr).find("td.value:first").before("<td class='blankTd trHeader'>&nbsp;</td>");
		});

		var height = $("#mainTableT").height();
		$("#ThtmlGrid").css("height", height);
	}
	
}


//최근시점 변경 이벤트
function fn_recentYear_set(prdSe){
	if(prdSe != 'Y'){
		$("#samePrdse_"+prdSe).val("");
		fn_SameTimeSelect(prdSe);
	}else{

		var chkYear = 0;
		var popTree =  $.ui.fancytree.getTree("#timePopList" + prdSe);
		
		var year = $("#samePrdseYear_"+prdSe).val();
		
		popTree.visit(function(node){							
			if(year != ""){
				if(year > chkYear){
					chkYear++;
					node.setSelected(true);
				}else{
					node.setSelected(false);
				}
			}else{
				node.setSelected(false);
			}
		});
	}
}

/************************************************************************
함수명 : fn_SameTimeSelect()
설   명 : 월,격월,분기에 대해서 특정 월이나 분기를 일괄 설정
작성일 : 2021-07-12

date         author      note
----------   -------     -------------------
2021-07-12        정창호		   최초생성
************************************************************************/

function fn_SameTimeSelect(prdSe){
	
	var buff= $("#samePrdse_"+prdSe).val();
	var sliceValue = "";
	var chkYear = 0;
	var maxYear = 0;
	var leftYear = 0;
	if(buff.length == 1){
		if(buff != "all"){
			buff = "0"+buff;
		}
	}
	if(buff!=""){
		
		var popTree =  $.ui.fancytree.getTree("#timePopList" + prdSe);
	
		var year = $("#samePrdseYear_"+prdSe).val();
		
		popTree.visit(function(node){							
			leftValue = node.title;
			leftYear = leftValue.substr(0, 4);
			if(maxYear < leftYear){
				maxYear = leftYear;
			}
			if(leftValue.length >= 2){
				if(prdSe == 'M'){
					sliceValue = leftValue.substr(leftValue.length - 2, 2);
				}else{
					sliceValue = "0"+leftValue.substr(leftValue.length - 3, 1);
				}
			}
			if(buff == sliceValue){
				if(year != ""){
					if(year > chkYear){
						chkYear++;
						node.setSelected(true);
					}else{
						node.setSelected(false);
					}
				}else{
					node.setSelected(true);
				}
				
			}else if(buff == "all"){
				if(year != ""){
					if(maxYear - year < leftYear){
						node.setSelected(true);
					}else{
						node.setSelected(false);
					}
				}else{
					node.setSelected(true);
				}	
			}else{
				node.setSelected(false);
			}
		});
		
	}
}


/************************************************************************
함수명 : fn_chk_time_all()
설   명 : 시점 팝업 시점 전체선택 - 전체해제
작성일 : 2021-07-12

date         author      note
----------   -------     -------------------
2021-07-29        정창호		   최초생성
************************************************************************/
function fn_chk_time_all(prdSe){
	var checked = $("#chk_time_all_" + prdSe).is(":checked");
	
	var popTree =  $.ui.fancytree.getTree("#timePopList" + prdSe);
	popTree.visit(function(node){							
		
		if(checked){
			node.setSelected(true);
		}else{
			node.setSelected(false);
		}
	});
}

/************************************************************************
함수명 : fn_data_search
설   명 : 데이터찾기 값 초기화
작성일 : 2021-08-31

date         author      note
----------   -------     -------------------
2021-07-29        정창호		   최초생성
************************************************************************/
function fn_data_search(){
	var type = $("#findOption").val();
	if(type != "0"){
//		$("#compValue01").val("");
//		$("#compValue02").val("");
//		$("#compValue").val("");
		$("#findData02").css("display", "none");
		$("#compValue").css("display", "");
	}else if (type == "0"){
//		$("#compValue01").val("");
//		$("#compValue02").val("");
//		$("#compValue").val("");
		$("#findData02").css("display", "");
		$("#compValue").css("display", "none");
	}
}

function fn_trHeaderWidthResize(){
	
	if(g_leftHeaderSize == 0) {
		g_trHeaderWidthResize = "DONE";
		return;
	}
	
	var tableArr = new Array(g_leftHeaderSize);
	
	for(var index=0; index < g_leftHeaderSize; index++){
		tableArr[index] = "<table id='fakeTable"+index+"' style='display:none;'>";
		tableArr[index] += "<thead>";
	}

	
	$("#mainTable thead tr").each(function(index, tr){
		for(var thIndex=0; thIndex < g_leftHeaderSize; thIndex++){
			tableArr[thIndex] += "<tr><th style='width:auto'>"+$(this).find("th.rowHead:eq("+thIndex+")").html()+"</th></tr>";			
		}				
	});
	
	for(var index=0; index < g_leftHeaderSize; index++){		
		tableArr[index] += "</thead>";
		tableArr[index] += "</tbody>";
	}
	
	
	$("#mainTable tbody tr").each(function(index, tr){
		for(var tdIndex=0; tdIndex < g_leftHeaderSize; tdIndex++){
			tableArr[tdIndex] += "<tr><td style='width:auto'>"+$(this).find("td:eq("+tdIndex+")").html()+"</td></tr>";
		}
	});
	
	for(var index=0; index < g_leftHeaderSize; index++){		
		tableArr[index] += "</tbody>";
		tableArr[index] += "</table>";
	}		
		
	for(var index=0; index < tableArr.length; index++){
		$('body').append(tableArr[index]);		
	}	
	
	
	for(var index=0; index < tableArr.length; index++){
		
		//console.log(tableArr.length);
		
		var tableName = "fakeTable"+index;
		$currTable = $("#"+tableName);
		
		//console.log($currTable);
		
		var currWidth = $currTable.width();
		//console.log(currWidth);
		
		if(currWidth > 147) {		
			$("#mainTable colgroup col:eq("+index+")").css("width", currWidth+30);
			$("#mainTableT colgroup col:eq("+index+")").css("width", currWidth+30);
		}
		
		
		$currTable.remove();
		
	}
	
	
	
	//setTimeout(6000);
	
	//fn_tableFix();
	
	g_trHeaderWidthResize = "DONE";
	
}



function fn_trHeaderWidthResize_bakup_slow(){	
	
	
	var maxWidth = 0;	
	var widthArr = new Array(g_leftHeaderSize);
	
	for(var i = 0 ; i < g_leftHeaderSize ; i++){
		
		$("#htmlGrid").find("table tbody tr").each(function(index, tr){
			var currWidth = $(tr).find("td:eq("+i+") span:last").attr("widthInfo");
			//var currWidth = $(tr).find("td:eq("+i+") span:last").width();//java 에서 직접 폭 조절할때			
			
			if(index == 0) { maxWidth = currWidth; }
			if(maxWidth < currWidth) { maxWidth = currWidth; }			
		});
		
		widthArr[i] = maxWidth;
	}

	//표측영역 폭 조절
	for(var i = 0 ; i < g_leftHeaderSize ; i++){		
		//colgroup 폭 조절
		$("#mainTable, #mainTableT").find("colgroup col:eq("+i+")").width( (widthArr[i]*1) + 45);
		
		//body td sapn 폭 조절	
		$("#htmlGrid").find("table tbody tr").each(function(index, tr){						
			$(tr).find("td:eq("+i+") span:last").width( widthArr[i] * 1 );
		});
	}
	
	
	
}

//구버전
function fn_trHeaderWidthResize_old(){
	
	if(g_leftHeaderSize == 0) return;
	
	var fakeTable = "<table id='fakeTable' style='display:none;'><thead></thead><tbody></tbody></table>";
	$('body').append(fakeTable);
	
	var tdIndex = g_leftHeaderSize - 1;

	$("#mainTable thead tr").each(function(index, tr){
		//var th = $(this).find("th.rowHead:eq("+tdIndex+")").text();
		var th = $(this).find("th.rowHead:eq("+tdIndex+")").html();
		var trHtml = "<tr><th>"+th+"</th></tr>";
		$("#fakeTable").find("thead").append(trHtml);
	});
		
	$("#mainTable tbody tr").each(function(index, tr){
		//var td = $(this).find("td:eq("+tdIndex+")").text();
		var td = $(this).find("td:eq("+tdIndex+")").html();
		var trHtml = "<tr><td>"+td+"</td></tr>";
		$("#fakeTable").find("tbody").append(trHtml);
	});
	//console.log($("#fakeTable").html());

	var tdWidth = $("#fakeTable").width();
	//console.log("tdWidth="+tdWidth);

	if(tdWidth < 147) {
		$("#fakeTable").remove();
		return;
	}

	$("#mainTable tbody tr").each(function(){
		$(this).find("td:eq("+tdIndex+") span:last").css("width", tdWidth);
		/*
		var beforeSpanWidth = $(this).find("td:eq("+tdIndex+") span:eq(1)").width();
		var lastSpanWidth = (tdWidth-beforeSpanWidth-10);
		$(this).find("td:eq("+tdIndex+")").css("width", tdWidth);
		$(this).find("td:eq("+tdIndex+") span:last").css("width", lastSpanWidth);
		*/
	});
	
	$("#mainTable, #mainTableT").find("colgroup col:eq("+tdIndex+")").css("width", tdWidth+35);
	$("#mainTable, #mainTableT").find("thead tr").each(function(){
		$(this).find("th.rowHead:eq("+tdIndex+") span:last").css("width", tdWidth);
	});
	
	$("#fakeTable").remove();
	
}

function fn_trHeaderWidthNormal(){
	
	if(g_leftHeaderSize == 0) return;
	
	var tdIndex = g_leftHeaderSize-1;
	
	
	$("#mainTable colgroup col:eq("+tdIndex+")").css("width", "170px");

	$("#mainTable thead tr").each(function(){
		$(this).find("th:eq("+tdIndex+") span:last").css("width", "147px");
	});
	
	
	$("#mainTable tbody tr").each(function(){
		$(this).find("td:eq("+tdIndex+") span:last").css("width", "147px");
	});

	$("#mainTableT colgroup col:eq("+tdIndex+")").css("width", "170px");
	
	$("#mainTableT thead tr").each(function(){
		$(this).find("th:eq("+tdIndex+") span:last").css("width", "147px");
	});
}



function selectElementContents(el){
	
	var body = document.body, range, sel;
	
	if(document.createRange && window.getSelection){
		
		range = document.createRange();
		sel = window.getSelection();
		sel.removeAllRanges();
		
		try{
			range.selectNodeContents(el);
			sel.addRange(range);
		}catch(e){
			range.selectNode(el);
			sel.addRange(range);
		};
		
	}else if(body.createTextRange){
		range = body.createTextRange();
		range.moveToElementText(el);
		range.select();
	}
}

function fnCopyTable(){
	
	
	$tableCopy = $("#htmlGrid #mainTable").clone();
	$tableCopy.find("thead>tr:last").remove();
	$tableCopy.attr("id", "mainTableForCopy");
	$tableCopy.css({"position" : "absolute", "top" : "-1000"});
	$tableCopy.find("tbody tr td.value span").not(".val").html("");
	$("#htmlGrid").append($tableCopy);
	
	$("#mainTableForCopy").find("tbody tr").removeClass("rowClick");
	$("#mainTableForCopy").find("tbody tr").children().removeClass("rowClick");
	$("#mainTableForCopy").find("a").remove();

	
	selectElementContents(document.getElementById("mainTableForCopy"));
	document.execCommand("Copy");
	fn_callAlertPop("copyTable");
	
	$("#mainTableForCopy").remove();
}


/************************************************************************
함수명 : fn_checkAllLevelInter()
설   명 : 국제통계 기구별 분류 리스트 선택후 조회
		Inter(국제기구), varOrdSn(분류순번), InterList(국가별정보리스트)
작성일 : 2024-07-22

date         author      note
----------   -------     -------------------
2024-07-22        이영석		   최초생성
************************************************************************/
function fn_checkAllLevelInter(Inter,varOrdSn, InterList) {
	
	var allList  = new Array(); //전체 분류리스트
	var chkList =  new Array(); //기구별 분류리스트
	var selectList = new Array(); //선택된 분류리스트
	
	if(Inter == "none"){ //전체 혹은 TOTAL 일경우(선택X)
	
	$.ui.fancytree.getTree("#fancytree_"+ varOrdSn).getRootNode().visit(function(node) {

		node.setSelected(true, {noEvents : true});
	});
	
	fn_changeMultiselectVal("multiSelect_"+ varOrdSn, "fancytree_"+ varOrdSn);
		
	fn_setDefaultClassArr("fancytree_"+ varOrdSn);

	fn_setPivotColChk();
	fn_searchTree(true);
	}
	else{ //국제기구가 선택이 되었을 경우

		//dataOpt 파라미터별 분류 정보 이름 가져오기
		for(var i =0; i< InterList.length; i++){
			if(g_dataOpt == "ko"){
				chkList.push(InterList[i].scrKor);
			}else if(g_dataOpt == "en"){chkList.push(InterList[i].scrEng);}
			else if(g_dataOpt == "cd"){chkList.push(InterList[i].itmId);}
			else if(g_dataOpt == "cdko"){chkList.push(InterList[i].itmId + " " +InterList[i].scrKor);}
			else if(g_dataOpt == "cden"){chkList.push(InterList[i].itmId + " " +InterList[i].scrEng);}
		}
		
		
		$.ui.fancytree.getTree("#fancytree_"+ varOrdSn).getRootNode().visit(function(node) {
			allList.push(node.title);	
		});
	
	
		for(var i=0;i< allList.length; i++){
			for(var j=0; j<chkList.length; j++){
				if(allList[i] === chkList[j]){
					selectList.push(allList[i]);
				}
			}
		}	
		
		$.ui.fancytree.getTree("#fancytree_"+ varOrdSn).visit(function(node) {
	
		node.setSelected(false, {noEvents : true}); //전체 분류 리스트 체킹 해제
		
		for(var i=0; i<selectList.length; i++){
			if(node.title == selectList[i]){
				node.setSelected(true);  //해당 기구별 분류만 체킹
			}
		}
		});
		fn_setDefaultClassArr("fancytree_"+ varOrdSn);

		fn_setPivotColChk();
		fn_searchTree(true);
	}
}

var fn_Copy = function() {
	const $url = $("#urlText");
	$url.select();
	document.execCommand('copy');
}