# xml formats for libvirt


miq_storage_pool = """
<pool type='dir'>
  <name>{name}</name>
  <target>
    <path>{path}</path>
      <permissions>
          <mode>0755</mode>
          <owner>-1</owner>
          <group>-1</group>
      </permissions>
  </target>
</pool>
"""

miq_volume = """
<volume>
    <name>{name}.{format}</name>
    <allocation>0</allocation>
    <capacity unit="G">{size}</capacity>
    <target>
        <format type="qcow2"/>
        <path>{path}/{name}.{format}</path>
        <permissions>
            <owner>107</owner>
            <group>107</group>
            <mode>0744</mode>
            <label>virt_image_t</label>
        </permissions>
    </target>
</volume>
"""

miq_ap = """
<domain type='kvm'>
    <name>{name}</name>
    <description>{version}</description>
    <memory unit='G'>{memory}</memory>
    <currentMemory unit='G'>{memory}</currentMemory>
    <vcpu placement='static'>1</vcpu>
    <resource>
        <partition>/machine</partition>
    </resource>
    <os>
        <type arch='x86_64' machine='pc-i440fx-2.11'>hvm</type>
        <boot dev='hd'/>
    </os>
        <features>
            <acpi/>
            <apic/>
            <vmport state='off'/>
        </features>
    <clock offset='utc'>
        <timer name='rtc' tickpolicy='catchup'/>
        <timer name='pit' tickpolicy='delay'/>
        <timer name='hpet' present='no'/>
    </clock>
    <on_poweroff>destroy</on_poweroff>
    <on_reboot>restart</on_reboot>
    <on_crash>destroy</on_crash>
    <pm>
        <suspend-to-mem enabled='no'/>
        <suspend-to-disk enabled='no'/>
    </pm>
    <devices>
        <emulator>/usr/bin/qemu-kvm</emulator>
        <disk type='file' device='disk'>
          <driver name='qemu' type='qcow2'/>
          <source file='{path}/{base_img}'/>
          <backingStore/>
          <target dev='vda' bus='virtio'/>
          <alias name='virtio-disk0'/>
          <address type='pci' domain='0x0000' bus='0x00' slot='0x07' function='0x0'/>
        </disk>
        <disk type='file' device='disk'>
          <driver name='qemu' type='qcow2'/>
          <source file='{path}/{db_img}'/>
          <backingStore/>
          <target dev='vdb' bus='virtio'/>
          <alias name='virtio-disk1'/>
          <address type='pci' domain='0x0000' bus='0x00' slot='0x08' function='0x0'/>
        </disk>
        <interface type='network'>
          <source network='default' bridge='virbr0'/>
          <target dev='vnet0'/>
          <model type='virtio'/>
          <alias name='net0'/>
          <address type='pci' domain='0x0000' bus='0x00' slot='0x03' function='0x0'/>
        </interface>
        <input type='mouse' bus='ps2'>
          <alias name='input1'/>
        </input>
        <input type='keyboard' bus='ps2'>
          <alias name='input2'/>
        </input>
        <graphics type='spice' port='5900' autoport='yes' listen='127.0.0.1'>
          <listen type='address' address='127.0.0.1'/>
          <image compression='off'/>
        </graphics>
        <sound model='ich6'>
          <alias name='sound0'/>
          <address type='pci' domain='0x0000' bus='0x00' slot='0x04' function='0x0'/>
        </sound>
        <video>
          <model type='qxl' ram='65536' vram='65536' vgamem='16384' heads='1' primary='yes'/>
          <alias name='video0'/>
          <address type='pci' domain='0x0000' bus='0x00' slot='0x02' function='0x0'/>
        </video>
    </devices>
</domain>
"""
