---@class RichText : Object
RichText = Object:extendAs("factorio.RichText")
RichText._ = {}

---@public
---@param text string
---@return string
function RichText.keySequence(text)
    return RichText.fontSemibold(RichText.colorBlue(text))
end

---@public
---@param type string
---@param name string
---@return string icon which fits into 3 monospaces
function RichText.icon3Monospaces(type, name)
    return RichText.fontMonospacedIcon3Spaces(RichText.icon(type, name))
end

---@public
---@param type string
---@param name string
---@return string
function RichText.icon(type, name)
    if not (type == "img"
            or type == "item"
            or type == "technology"
            or type == "recipe"
            or type == "fluid"
            or type == "entity"
            or type == "quality"
    ) then
        type = "item"
    end
    return "[" .. type .. "=" .. name .. "]"
end

---@public
---@return string
function RichText.iconEmpty()
    return RichText._.iconEmpty
end
RichText._.iconEmpty = RichText.icon("img", Toolbars.icons.empty)

---@public
---@param count number
---@return string
function RichText.countColumn(count)
    return RichText.leftPad(4, RichText.count(count))
end

function RichText.fontEnd()
    return RichText._.fontEnd
end
RichText._.fontEnd = "[/font]"

---@public
---@param text string
---@return string
function RichText.fontBold(text)
    return string.format(RichText._.fontBoldFormat, text)
end

---@public
---@return string
function RichText.fontBoldStart()
    return RichText._.fontBoldStart
end
RichText._.fontBoldStart = "[font=default-bold]"
RichText._.fontBoldFormat = RichText._.fontBoldStart .. "%s" .. RichText._.fontEnd

---@public
---@param text string
---@return string
function RichText.fontSemibold(text)
    return string.format(RichText._.fontSemiboldFormat, text)
end

---@public
---@return string
function RichText.fontSemiboldStart()
    return RichText._.fontSemiboldStart
end
RichText._.fontSemiboldStart = "[font=default-semibold]"
RichText._.fontSemiboldFormat = RichText._.fontSemiboldStart .. "%s" .. RichText._.fontEnd

---@public
---@param text string
---@return string
function RichText.fontLarge(text)
    return string.format(RichText._.fontLargeFormat, text)
end

---@public
---@return string
function RichText.fontLargeStart()
    return RichText._.fontLargeStart
end
RichText._.fontLargeStart = "[font=default-large]"
RichText._.fontLargeFormat = RichText._.fontLargeStart .. "%s" .. RichText._.fontEnd

---@public
---@param text string
---@return string
function RichText.fontSmall(text)
    return string.format(RichText._.fontSmallFormat, text)
end

---@public
---@return string
function RichText.fontSmallStart()
    return RichText._.fontSmallStart
end
RichText._.fontSmallStart = "[font=default-small]"
RichText._.fontSmallFormat = RichText._.fontSmallStart .. "%s" .. RichText._.fontEnd

---@public
---@param text string
---@return string
function RichText.fontSmallSemibold(text)
    return string.format(RichText._.fontSmallSemiboldFormat, text)
end

---@public
---@return string
function RichText.fontSmallSemiboldStart()
    return RichText._.fontSmallSemiboldStart
end
RichText._.fontSmallSemiboldStart = "[font=default-small-semibold]"
RichText._.fontSmallSemiboldFormat = RichText._.fontSmallSemiboldStart .. "%s" .. RichText._.fontEnd

---@public
---@param text string
---@return string
function RichText.fontMonospaced(text)
    return string.format(RichText._.fontMonospacedFormat, text)
end

---@public
---@return string
function RichText.fontMonospacedStart()
    return RichText._.fontMonospacedStart
end
RichText._.fontMonospacedStart = "[font=default]"
RichText._.fontMonospacedFormat = RichText._.fontMonospacedStart .. "%s" .. RichText._.fontEnd

---@public
---@return string
function RichText.monospace()
    return RichText._.monospace
end
RichText._.monospace = RichText.fontMonospaced(" ")

---@private
---@param text string
---@return string
function RichText.fontMonospacedIcon3Spaces(text)
    return string.format(RichText._.fontMonospacedIcon3SpacesFormat, text)
end

---@private
---@return string
function RichText.fontMonospacedIcon3SpacesStart()
    return RichText._.fontMonospacedIcon3SpacesStart
end
RichText._.fontMonospacedIcon3SpacesStart = "[font=default]"
RichText._.fontMonospacedIcon3SpacesFormat = RichText._.fontMonospacedIcon3SpacesStart .. "%s" .. RichText._.fontEnd

---@public
---@return string
function RichText.colorEnd()
    return RichText._.colorEnd
end
RichText._.colorEnd = "[/color]"

---@public
---@param text string
---@return string
function RichText.colorCaption(text)
    return string.format(RichText._.colorCaptionFormat, text)
end

---@public
---@return string
function RichText.colorCaptionStart()
    return RichText._.colorCaptionStart
end
RichText._.colorCaptionStart = "[color=255,230,192]"
RichText._.colorCaptionFormat = RichText._.colorCaptionStart .. "%s" .. RichText._.colorEnd

---@public
---@param text string
---@return string
function RichText.colorWhite(text)
    return string.format(RichText._.colorWhiteFormat, text)
end

---@public
---@return string
function RichText.colorWhiteStart()
    return RichText._.colorWhite
end
RichText._.colorWhite = "[color=1,1,1]"
RichText._.colorWhiteFormat = RichText._.colorWhite .. "%s" .. RichText._.colorEnd

---@public
---@param text string
---@return string
function RichText.colorBlue(text)
    return string.format(RichText._.colorBlueFormat, text)
end

---@public
---@return string
function RichText.colorBlueStart()
    return RichText._.colorBlue
end
RichText._.colorBlue = "[color=128,206,240]"
RichText._.colorBlueFormat = RichText._.colorBlue .. "%s" .. RichText._.colorEnd

---@public
---@param text string
---@return string
function RichText.colorGray(text)
    return string.format(RichText._.colorGrayFormat, text)
end

---@public
---@return string
function RichText.colorGrayStart()
    return RichText._.colorGray
end
RichText._.colorGray = "[color=0.7,0.7,0.7]"
RichText._.colorGrayFormat = RichText._.colorGray .. "%s" .. RichText._.colorEnd

---@public
---@param text string
---@return string
function RichText.colorGreen(text)
    return string.format(RichText._.colorGreenFormat, text)
end

---@public
---@return string
function RichText.colorGreenStart()
    return RichText._.colorGreen
end
RichText._.colorGreen = "[color=62,236,87]"
RichText._.colorGreenFormat = RichText._.colorGreen .. "%s" .. RichText._.colorEnd

---@public
---@param text string
---@return string
function RichText.colorLightOrange(text)
    return string.format(RichText._.colorLightOrangeFormat, text)
end

---@public
---@return string
function RichText.colorLightOrangeStart()
    return RichText._.colorLightOrange
end
RichText._.colorLightOrange = "[color=1,0.74,0.40]"
RichText._.colorLightOrangeFormat = RichText._.colorLightOrange .. "%s" .. RichText._.colorEnd

---@public
---@param text string
---@return string
function RichText.colorRed(text)
    return string.format(RichText._.colorRedFormat, text)
end

---@public
---@return string
function RichText.colorRedStart()
    return RichText._.colorRed
end
RichText._.colorRed = "[color=255,136,136]"
RichText._.colorRedFormat = RichText._.colorRed .. "%s" .. RichText._.colorEnd

---@public
---@param text string
---@return string
function RichText.label(text)
    return string.format(RichText._.labelFormat, text)
end

---@public
---@return string
function RichText.labelStart()
    return RichText._.labelStart
end

---@public
---@return string
function RichText.labelEnd()
    return RichText._.labelEnd
end
RichText._.labelStart = RichText.fontSemiboldStart() .. RichText.colorCaptionStart()
RichText._.labelEnd = RichText._.colorEnd .. RichText._.fontEnd
RichText._.labelFormat = RichText._.labelStart .. "%s" .. RichText._.labelEnd

---@public
---@param text string
---@param width number
---@return string
function RichText.leftPad(width, text)
    return string.format("%" .. tostring(width) .. "s", text)
end

---@public
---@param number number
---@return string
function RichText.count(number)
    local index = 1
    while number >= 1000 do
        number = number / 1000
        index = index + 1
    end
    if index == 1 then
        if 0.01 < number and number < 1 then
            return string.format("%.2f", number)
        else
            return string.format("%.3g", number)
        end
    elseif number < 10 then
        return string.format("%.1f%s", math.floor(number * 10) / 10, RichText._.numberSuffixes[index])
    else
        return string.format("%d%s", number, RichText._.numberSuffixes[index])
    end
end
RichText._.numberSuffixes = { "", "k", "M", "G", "T", "P", "E", "Z", "Y" }
RichText._.numberSuffixesSize = #RichText._.numberSuffixes
