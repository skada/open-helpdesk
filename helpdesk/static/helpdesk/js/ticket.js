require([ "jquery", "jquery-ui/jquery-ui.min", ], function ($) {
    var ticketInfos = "#ticket_infos";
    var tabsIds = ['ticket_data', 'messages', 'changestatuslog'];
    var currentUrl = $(location).attr('pathname');

    helpdeskGetObjectTools(currentUrl);

    // remove 'add-another' link/button
    $('a.add-another').remove();

    // settings and managements of tabs
    $(ticketInfos).tabs();

    for(var key in tabsIds) {
        $(ticketInfos).css("margin-bottom",
            $(ticketInfos + " #tab_" + tabsIds[key] +
                " fieldset").css("margin-bottom"));
        $(ticketInfos + " #tab_" + tabsIds[key] +
                " fieldset").css("margin-bottom", "0");
    }

    $('a.related_ticket, a.view_report').button();

    helpdeskFinalize($);
});
