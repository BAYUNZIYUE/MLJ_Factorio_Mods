if not package.loading then package.loading = {} end
function import(module)
    module = "src." .. module
    if package.loading[module] == nil then
        package.loading[module] = true
        require(module)
        package.loading[module] = nil
    end
end
