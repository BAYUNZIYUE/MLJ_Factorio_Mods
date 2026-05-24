---@class Object
---@field private __index table
---@field private __name string
Object = { __name = "lang.Object" }

---[class]
---@public
---@param name string
---@return self
function Object:extendAs(name)
    self.__index = self
    local class = { __name = name }
    class.__index = class
    return setmetatable(class, self)
end

---@public
---@return self
function Object.new()
    return Object:super({})
end

---[class] Don't use on an object, self refers then to the leaf not a Class of a current method.
---@public
---@generic S : Object
---@param super S @instance of super class to create an object or nothing to get a super Class
---@return self @instance of self class or super Class
function Object:super(super)
    if super then
        return setmetatable(super, self)
    else
        return getmetatable(self:class()).__index
    end
end

---@public
---@generic C : Object
---@param class C
---@return boolean
function Object:isInstanceOf(class)
    return self:class() == class
end

---@public
---@return self
function Object:class()
    return self.__index
end

---@public
---@return string
function Object:className()
    return self.__name
end

---@public
---@generic T
---@param type T
---@return T
function Object:cast(type)
    return self
end

---@class A : Object
A = Object:extendAs("A")
function A.new()
    local this = A:super(Object.new())
    this._field = "A._field"
    return this
end
function A:method()
    return "A:method(): " .. self._field
end

local a = A.new()
assert(a:class() == A)
assert(a:className() == "A")
assert(a:super() == Object)
assert(a:method() == "A:method(): A._field")

---@class B : A
B = A:extendAs("B")
function B.new()
    local this = B:super(A.new())
    this._field = "B._field"
    return this
end

local b = B.new()
assert(b:class() == B)
assert(b:className() == "B")
assert(b:super() == A)
assert(b:method() == "A:method(): B._field")

---@class C : B
C = B:extendAs("C")
function C.new()
    return C:super(B.new())
end
function C:method()
    return "C:method(): " .. self._field
end

local c = C.new()
assert(c:class() == C)
assert(c:className() == "C")
assert(c:super() == B)
assert(c:method() == "C:method(): B._field")

---@class D : C
D = C:extendAs("D")
function D.new()
    local this = D:super(C.new())
    this._field = "D._field" .. " " .. this._field
    if this._unknown == nil then end
    return this
end

local d = D.new()
assert(d:class() == D)
assert(d:className() == "D")
assert(d:super() == C)
assert(d:method() == "C:method(): D._field B._field")

assert(D:super():super():super() == A)
assert(D:super():super():super():className() == "A")

print("Object is working")
