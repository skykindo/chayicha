# 渠道配置（本地 CSV）

**完整指令与 CSV 导入说明见 [NPM-COMMANDS.md](./NPM-COMMANDS.md)**（第三节～第五节）。

要点：

- WEB → `web-channels.csv` + `npm run web:import`
- VISION → `vision-channels.csv` + `npm run vision:import`
- 删 CSV 行要从库同步删除 → 加 `--sync`
- 历史价格 `PriceStream` 不会因渠道 import 而删除
