<template>
  <bk-exception :scene="scene" :type="type">
    <template v-if="['search-empty', '500'].includes(type)" #default>
      <template v-if="type === 'search-empty'">
        <p class="empty-title">{{ $t('搜索结果为空') }}</p>
        <i18n tag="p" class="empty-desc" path="可以尝试调整关键词或清空筛选条件">
          <bk-link theme="primary" class="empty-btn" @click="() => handleClick('clear')">
            {{ $t('清空筛选条件') }}
          </bk-link>
        </i18n>
      </template>
      <template v-if="type === '500'">
        <div class="empty">
          <p class="empty-title">{{ $t('获取数据异常') }}</p>
          <p class="empty-desc">
            <bk-link theme="primary" class="empty-btn" @click="() => handleClick('refresh')">
              {{ $t('刷新') }}
            </bk-link>
          </p>
        </div>
      </template>
    </template>
  </bk-exception>
</template>
<script lang="ts">
import { Component, Vue, Prop } from 'vue-property-decorator';

@Component({ name: 'NmException' })
export default class CopyDropdown extends Vue {
  @Prop({ type: String, default: 'empty' }) protected readonly type!: string;
  @Prop({ type: String, default: 'part' }) protected readonly scene!: string;

  public handleClick(clickType: string) {
    this.$emit(`empty-${clickType}`);
  }
}
</script>

<style lang="postcss" scoped>
  .empty-title {
    line-height: 22px;
    font-size: 14px;
    color: #63656e;
  }

  .empty-desc {
    display: flex;
    align-items: center;
    margin-top: 8px;
    line-height: 20px;
    font-size: 12px;
    color: #979ba5;
  }
  .empty-btn {
    margin-left: 4px;
    .bk-link-text {
      font-size: 12px;
    }
  }
</style>
