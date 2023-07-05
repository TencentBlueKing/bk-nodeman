<template>
  <div :class="`bk-exception ${scene === 'part' ? 'exception-part' : ''}`">
    <div :class="`bk-exception-img ${scene === 'part' ? 'part' : 'page'}-img`">
      <img :src="image" alt="" class="exception-image">
    </div>
    <div :class="`bk-exception-text ${scene === 'part' ? 'part' : 'page'}-text`">
      <template v-if="'empty' === typeDisplay">{{ $t('暂无数据') }}</template>
      <template v-if="['search-empty', '500'].includes(typeDisplay)">
        <template v-if="typeDisplay === 'search-empty'">
          <p class="empty-title">{{ $t('搜索结果为空') }}</p>
          <i18n tag="p" class="empty-desc" path="可以尝试调整关键词或清空筛选条件">
            <bk-link theme="primary" class="empty-btn" @click="() => handleClick('clear')">
              {{ $t('清空筛选条件') }}
            </bk-link>
          </i18n>
        </template>
        <template v-if="typeDisplay === '500'">
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
    </div>
  </div>
</template>

<script lang="ts">
import { Component, Vue, Prop, Watch } from 'vue-property-decorator';
import imgEmptyData from '@/images/empty-data.png';
import imgEmptySearch from '@/images/empty-search.png';
import imgEmptyAbnormal from '@/images/empty-abnormal.png';

@Component({ name: 'NmException' })
export default class CopyDropdown extends Vue {
  @Prop({ type: Boolean, default: false }) protected readonly delay!: false;
  @Prop({ type: String, default: 'empty' }) protected readonly type!: string; // search-empty empty 500
  @Prop({ type: String, default: 'part' }) protected readonly scene!: string;

  private oldType = this.type;
  private image = '';

  private get typeDisplay() {
    return this.delay ? this.oldType : this.type;
  }
  private created() {
    let image = '';
    switch (this.type) {
      case 'empty':
        image = imgEmptyData;
        break;
      case 'search-empty':
        image = imgEmptySearch;
        break;
      case '500':
        image = imgEmptyAbnormal;
        break;
    }
    this.image = image;
  }

  @Watch('delay', { immediate: true })
  private changeDelay(value: boolean) {
    if (!value) {
      this.oldType = this.type;
    }
  }

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
    /deep/ .bk-link-text {
      font-size: 12px;
    }
  }
</style>
