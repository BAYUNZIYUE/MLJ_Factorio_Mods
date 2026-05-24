if not package.loading then package.loading = {} end
function import(module)
    if package.loading[module] == nil then
        package.loading[module] = true
        require(module)
        package.loading[module] = nil
    end
end
