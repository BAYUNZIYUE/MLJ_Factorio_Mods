---@class Memento : Object
---@generic V
---@field private _supplier fun():V
---@field private _value V
Memento = Object:extendAs("Memento")

---@public
---@generic V
---@param supplier fun():V
---@return Memento<V>
function Memento.new(supplier)
    local this = Memento:super(Object.new())
    this._supplier = supplier
    this._set = false
    this._value = nil
    return this
end

---@public
---@generic V
---@return V value
function Memento:value()
    if not self._set then
        self._value = self._supplier()
        self._set = true
    end
    return self._value
end
