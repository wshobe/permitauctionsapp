
//Convert a number to a formatted money string
function format_money(num) {
    num = num.toFixed(2) // 2 decimal places
    return "$" + String(num)
}