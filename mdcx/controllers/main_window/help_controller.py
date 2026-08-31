from __future__ import annotations

from .responsive_layout import show_responsive_overlay


class HelpControllerMixin:
    def pushButton_tips_normal_mode_clicked(self):
        self._show_tips(self.Ui.pushButton_tips_normal_mode.toolTip())

    def pushButton_tips_sort_mode_clicked(self):
        self._show_tips(self.Ui.pushButton_tips_sort_mode.toolTip())

    def pushButton_tips_update_mode_clicked(self):
        self._show_tips(self.Ui.pushButton_tips_update_mode.toolTip())

    def pushButton_tips_read_mode_clicked(self):
        self._show_tips(self.Ui.pushButton_tips_read_mode.toolTip())

    def pushButton_tips_soft_clicked(self):
        self._show_tips(self.Ui.pushButton_tips_soft.toolTip())

    def pushButton_tips_hard_clicked(self):
        self._show_tips(self.Ui.pushButton_tips_hard.toolTip())

    def _show_tips(self, msg):
        self.Ui.textBrowser_show_tips.setText(msg)
        show_responsive_overlay(self, self.Ui.widget_show_tips)

    def pushButton_scrape_note_clicked(self):
        self._show_tips("""<html>
<head/>
<body>
  <p><span style=" font-weight:700;">所有可用网站:</span></p>
  <li>airav_cc</li>
  <li>avbase</li>
  <li>avsex</li>
  <li>avsox</li>
  <li>cableav</li>
  <li>cnmdb</li>
  <li>dmm</li>
  <li>faleno</li>
  <li>fantastica</li>
  <li>fc2</li>
  <li>fc2club</li>
  <li>fc2hub</li>
  <li>fc2ppvdb</li>
  <li>freejavbt</li>
  <li>getchu</li>
  <li>giga</li>
  <li>hdouban</li>
  <li>hscangku</li>
  <li>iqqtv</li>
  <li>jav321</li>
  <li>javbus</li>
  <li>javday</li>
  <li>javdb</li>
  <li>javlibrary</li>
  <li>kin8</li>
  <li>love6</li>
  <li>lulubar</li>
  <li>madouqu</li>
  <li>mdtv</li>
  <li>missav</li>
  <li>mgstage</li>
  <li>7mmtv</li>
  <li>mywife</li>
  <li>prestige</li>
  <li>theporndb</li>
  <li>xcity</li>
  <li>dahlia</li>
  <li>getchu_dmm</li>
  <li>official</li>
  <p><span style=" font-weight:700;">指定类型影片可指定刮削网站:<span></p>
  <p>· 欧美：theporndb </p>
  <p>· 国产：mdtv、madouqu、hdouban、cnmdb、love6</p>
  <p>· 里番：getchu_dmm </p>
  <p>· Mywife：mywife </p>
  <p>· GIGA：giga </p>
  <p>· Kin8：Kin8 </p>
</body>
</html>""")

    def pushButton_field_tips_nfo_clicked(self):
        msg = """
<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n\
<movie>\n\
    <plot><![CDATA[剧情简介]]></plot>\n\
    <outline><![CDATA[剧情简介]]></outline>\n\
    <originalplot><![CDATA[原始剧情简介]]></originalplot>\n\
    <tagline>发行日期 XXXX-XX-XX</tagline> \n\
    <premiered>发行日期</premiered>\n\
    <releasedate>发行日期</releasedate>\n\
    <release>发行日期</release>\n\
    <num>番号</num>\n\
    <title>标题</title>\n\
    <originaltitle>原始标题</originaltitle>\n\
    <sorttitle>类标题 </sorttitle>\n\
    <mpaa>家长分级</mpaa>\n\
    <customrating>自定义分级</customrating>\n\
    <actor>\n\
        <name>名字</name>\n\
        <type>类型：演员</type>\n\
    </actor>\n\
    <director>导演</director>\n\
    <rating>评分</rating>\n\
    <criticrating>影评人评分</criticrating>\n\
    <votes>想看人数</votes>\n\
    <year>年份</year>\n\
    <runtime>时长</runtime>\n\
    <series>系列</series>\n\
    <set>\n\
        <name>合集</name>\n\
    </set>\n\
    <studio>片商/制作商</studio> \n\
    <maker>片商/制作商</maker>\n\
    <publisher>厂牌/发行商</publisher>\n\
    <label>厂牌/发行商</label>\n\
    <tag>标签</tag>\n\
    <genre>风格</genre>\n\
    <cover>背景图地址</cover>\n\
    <poster>封面图地址</poster>\n\
    <trailer>预告片地址</trailer>\n\
    <website>刮削网址</website>\n\
</movie>\n\
        """
        self._show_tips(msg)
