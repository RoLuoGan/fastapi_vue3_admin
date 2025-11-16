<template>
  <div class="dashboard-container">
    <el-card shadow="hover">
      <div class="flex flex-wrap">
        <!-- 左侧问候语区域 -->
        <div class="flex-1 flex items-start">
          <img class="w80px h80px rounded-full" :src="userStore.basicInfo.avatar + '?imageView2/1/w/80/h/80'" />
          <div class="ml-5">
            <div class="text-20px font-bold mb-5px">
              {{ timefix }}{{ userStore.basicInfo.name }}，{{ welcome }}
            </div>
            <p class="text-sm text-gray">今日天气晴朗，气温在15℃至25℃之间，东南风。</p>
          </div>
        </div>
      </div>
    </el-card>
  </div>
</template>

<script setup lang="ts">
defineOptions({
  name: "Home",
  inheritAttrs: false,
});

import { useUserStore } from "@/store/modules/user.store";
import { greetings } from '@/utils/common';

const timefix = greetings();
const welcome = '祝你开心每一天！';

const userStore = useUserStore();
</script>

<style lang="scss" scoped>
.dashboard-container {
  position: relative;
  padding: 16px;

  .github-corner {
    position: absolute;
    top: 0;
    right: 0;
    z-index: 1;
    border: 0;
  }

  .version-item {
    padding: 16px;
    margin-bottom: 12px;
    background: var(--el-fill-color-lighter);
    border-radius: 8px;
    transition: all 0.2s;

    &.latest-item {
      background: var(--el-color-primary-light-9);
      border: 1px solid var(--el-color-primary-light-5);
    }

    &:hover {
      transform: translateX(5px);
    }

    .version-content {
      margin-bottom: 12px;
      font-size: 13px;
      line-height: 1.5;
      color: var(--el-text-color-secondary);
    }
  }
}
</style>
