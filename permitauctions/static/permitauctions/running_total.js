
//Add event listeners to bid fields
function add_bid_listeners() {
    // grab table containing the bid forms by its id
    var bid_form = $("#bid_form"); 
    // for each select element child add a event listener for 'change' events
    var selectors = bid_form.find("select").on("change", bid_listen);
}

//Event listener for bid fields changing
function bid_listen() {
    var sum = 0;

    // grab table containing the bid forms by its id
    var bid_form = $("#bid_form"); 
    //grab all children select elements
    var selectors = bid_form.find("select") ;
    
    //iterate through select elements
    for(var i = 0; i < selectors.length; i++) {
        var selected = $(selectors[i]).val();
        //the value of the selected element is a string, must cast it as a Number
        //multiplier is set in the Auction.html template
        sum += Number(selected) * multiplier;
    }

    display_total(sum);

    //money is a variable set in the Auction.html template
    // it is the player's total money
    if(!allow_deficit && sum > money) {
        disable_submit();
    }
    else {
        enable_submit();
    }
}

//Display the running total on the page
function display_total(total) {
    var bid_form = $("#bid_form");
    
    //remove the element with id total_message if it exists
    $("#total_message").remove();

    var message = "<p>Total: " + format_money(total) + "</p>";
    //money is a variable set in the Auction.html template
    // it is the player's total money
    if(total > money) {
        message += "<p>You are bidding more money than you have</p>";
    }

    var to_display = "<tr id='total_message'><td>" + message +  "</td></tr>";
    //append new message to bid_form table
    bid_form.append(to_display);
}

function disable_submit() {
    $("button").prop("disabled", true);
    $("#disabled-text").text("You can not proceed to the next page until you fix your bid amount");
}

function enable_submit() {
    $("button").prop("disabled", false);
    $("#disabled-text").text(""); // set the text to the empty string
}
